from stl import mesh
from mpl_toolkits import mplot3d
from matplotlib import pyplot as plt
# import imageio
from PIL import Image
import numpy as np
import tqdm
import cmath
# import matplotlib.tri as mtri
import os
import pandas as pd


def show_render(stl_file_path):
    # Create a new plot
    figure = plt.figure()
    axes = mplot3d.Axes3D(figure)

    # Load the STL files and add the vectors to the plot
    your_mesh = mesh.Mesh.from_file(stl_file_path)
    axes.add_collection3d(mplot3d.art3d.Poly3DCollection(your_mesh.vectors))

    # Auto scale to the mesh size
    scale = your_mesh.points.flatten(-1)
    axes.auto_scale_xyz(scale, scale, scale)

    # Show the plot to the screen
    plt.show()


def get_rel_polar(centroid, point):
    centroid_x, centroid_y = centroid
    x, y = point
    rel_rad, rel_phi = cmath.polar(complex(centroid_x - x, centroid_y - y))
    return rel_rad, rel_phi


class PixelGroup:
    """holds pixel-data for one image"""

    def __init__(self, img_path, emboss_width_mm, emboss_depth_mm):
        # path of source image
        self.img_path = img_path

        # image data
        self.img = Image.open(self.img_path).convert('LA')
        self.img.show()

        # array of darkness values
        # self.img_arr = np.asarray(self.img)[:, :, 0]
        self.img_arr = np.array(self.img)[:, :, 0]


        # pixel dimensions
        self.height, self.width = self.img_arr.shape

        # super-pixel dimensions
        self.super_pixel_height, self.super_pixel_width = self.height - 1, self.width - 1
        self.num_of_super_pixels = self.super_pixel_height * self.super_pixel_width
        # self.super_centroid = (self.width/2.0, self.height/2.0)

        self.super_centroid = (self.super_pixel_width/2.0, self.super_pixel_height/2.0)
        self.super_radius = max(self.super_centroid)

        # remove all data outside exclusion-radius
        for x in range(self.super_pixel_width):
            for y in range(self.super_pixel_height):
                rel_rad, rel_phi = get_rel_polar(centroid=self.super_centroid, point=(x, y))
                # add two-pixel buffer to outer edge
                if rel_rad > self.super_radius - 2:
                    self.img_arr[y, x] = 0

        # scaling values
        self.dx = float(emboss_width_mm) / self.width
        self.dy = self.dx
        self.dz = float(emboss_depth_mm) / (self.img_arr.max())

    @property
    def output_stl_path(self):
        """generate output file path for stl file"""
        head, tail = os.path.split(self.img_path)
        filename, ext = os.path.splitext(tail)
        new_tail = '{}.stl'.format(filename)
        new_path = os.path.join(head, new_tail)
        return new_path

    def super_pixel_gen(self):
        """generating function super-pixels"""
        # convert from pixel-coordinate-system to super-pixel-coordinate-system
        # each super-pixel represents two triangles (4 original pixels)

        # .   .   .
        # .   .   .     ->      .   .
        # .   .   .             .   .

        for x in range(self.super_pixel_width):
            for y in range(self.super_pixel_height):
                yield SuperPixel(img_arr=self.img_arr, img_height=self.height, img_width=self.width,
                                 super_centroid=self.super_centroid, super_radius=self.super_radius,
                                 x=x, y=y, dx=self.dx, dy=self.dy, dz=self.dz)

    def super_pixel_within_radius_gen(self):
        return (super_pixel for super_pixel in self.super_pixel_gen() if super_pixel.is_within_super_radius)

    @property
    def triangle_count(self):
        """number of trianlges in this pixel-group"""
        return 2 * self.num_of_super_pixels

    @property
    def all_open_points(self):
        open_points = []
        for super_pixel in tqdm.tqdm(self.super_pixel_within_radius_gen(), total=self.num_of_super_pixels):
            open_points.extend(super_pixel.open_points)

        open_points_df = pd.DataFrame(open_points)
        open_points_df.rename(columns={0: 'x', 1: 'y', 2: 'z'}, inplace=True)
        open_points_df[['rad', 'phi']] = open_points_df.apply(lambda row: get_rel_polar(centroid=self.super_centroid, point=(row['x'], row['y'])), axis=1, result_type='expand')

        # remove duplicates and sort
        open_points_df.drop_duplicates(subset=['x', 'y', 'z'], inplace=True)
        open_points_df.sort_values(['phi', 'rad'], inplace=True)


        for row in open_points_df.itertuples():
            yield row.x, row.y, row.z

    def make_stl(self):
        """make and save stl file"""
        stl = mesh.Mesh(np.zeros(self.triangle_count, dtype=mesh.Mesh.dtype))

        i = -1
        for pixel in tqdm.tqdm(self.super_pixel_within_radius_gen(), total=self.num_of_super_pixels):
            for triangle in pixel.triangles:
                i += 1
                for j in range(3):
                    stl.vectors[i][j] = triangle[j]

        # Write the mesh to file "cube.stl"
        stl.save(self.output_stl_path)


class SuperPixel:
    """A Super-Pixel is a collection of four pixels. Each Super-Pixel represents two triangles in the output STL"""
    def __init__(self, img_arr, img_height, img_width, super_centroid, super_radius, x, y, dx, dy, dz):
        self.img_arr = img_arr
        self.img_height, self.img_width = img_height, img_width

        # super x, y coordinate in picture
        self.x, self.y = x, y
        self.dx, self.dy, self.dz = dx, dy, dz

        self.super_centroid, self.super_radius = super_centroid, super_radius

        # coordinates relative to picture centroid
        self.rel_rad, self.rel_phi = get_rel_polar(centroid=self.super_centroid, point=(self.x, self.y))

        self.is_within_super_radius = self.rel_rad <= self.super_radius

    def coord_transform(self, coordinate_tuple):
        """perform scaling transformation"""
        x, y, z = coordinate_tuple
        new_x = x * self.dx
        # need to flip y-axis
        new_y = (self.img_height - y) * self.dy
        new_z = z * self.dz

        return new_x, new_y, new_z

    def z_coord(self, x, y):
        """get z-coord for x, y pair"""
        return self.img_arr[y, x]

    @property
    def vertices(self):
        """return dictionary of the scaled vertices for the current super-pixel"""

        corners = {
            'NW': (self.x, self.y),
            'NE': (self.x + 1, self.y),
            'SW': (self.x, self.y + 1),
            'SE': (self.x + 1, self.y + 1)
        }

        # do transformations here
        vertices = {corner: self.coord_transform((x, y, self.z_coord(x=x, y=y))) for corner, (x, y) in corners.items()}

        return vertices

    @property
    def triangles(self):
        """return list of the two triangles for the current Super-Pixel"""

        # gather vertices for the four corners
        v = self.vertices

        # find z elevation change for opposite corners
        diagonal_z_step_nw_se = abs(v['NW'][-1] - v['SE'][-1])
        diagonal_z_step_ne_sw = abs(v['NE'][-1] - v['SW'][-1])

        # shortest z-distance determines which diagonal is drawn
        if diagonal_z_step_nw_se < diagonal_z_step_ne_sw:
            triangles = [
                (v['NW'], v['NE'], v['SE']),
                (v['SE'], v['SW'], v['NW'])
            ]
        else:
            triangles = [
                (v['SW'], v['NW'], v['NE']),
                (v['NE'], v['SE'], v['SW'])
            ]

        return triangles

    @property
    def neighbors(self):
        """dictionary of super-pixel neighbors"""
        neighbors = {
            'N': (self.x, self.y + 1),
            'E': (self.x + 1, self.y),
            'S': (self.x, self.y - 1),
            'W': (self.x - 1, self.y)
        }
        return neighbors

    # TODO: for each missing neighbor, add the corresponding missing vertices
    @property
    def missing_neighbors(self):
        missing_neighbors = []
        for direction, neighbor in self.neighbors.items():
            rel_rad, rel_phi = get_rel_polar(centroid=self.super_centroid, point=neighbor)
            if rel_rad > self.super_radius:
                missing_neighbors.append(direction)

        return missing_neighbors

    @property
    def open_points(self):
        return (point for direction in self.missing_neighbors for corner, point in self.vertices.items() if direction in corner)


if __name__ == '__main__':
    print("starting script...")

    # input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\pics\images.jpg'
    # input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\pics\smile.gif'
    input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\pics\checkerboard.png'
    # input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\pics\samus2.png'
    # input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\pics\goomba.png'




    # input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\pics\mg_logo.gif'
    # PixelGroup(img_path=input_img_path, emboss_width_mm=1000, emboss_depth_mm=50).make_stl()
    temp = PixelGroup(img_path=input_img_path, emboss_width_mm=1000, emboss_depth_mm=50).all_open_points
    for x in temp:
        print(x)


    print("done!")
