from stl import mesh
from mpl_toolkits import mplot3d
from matplotlib import pyplot as plt
# import imageio
from PIL import Image
import numpy as np
import tqdm
# import matplotlib.tri as mtri
import os


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


class PixelGroup:

    def __init__(self, img_path):

        self.img_path = img_path

        self.img = Image.open(self.img_path).convert('LA')
        self.img.show()

        self.img_arr = np.asarray(self.img)[:, :, 0]

        self.height, self.width = self.img_arr.shape
        self.num_of_pixels = self.height * self.width

        # add extra row & column
        fixed_img_arr = np.append(self.img_arr, np.zeros(shape=(1, self.width)), axis=0)
        fixed_img_arr = np.append(fixed_img_arr, np.zeros(shape=(self.height + 1, 1)), axis=1)

        self.fixed_img_arr = fixed_img_arr

        emboss_depth_mm = 10
        emboss_width_mm = 1000

        self.dx = float(emboss_width_mm) / self.width
        self.dy = self.dx * self.height / self.width
        self.dz = float(emboss_depth_mm) / (self.img_arr.max())

    @property
    def output_stl_path(self):
        head, tail = os.path.split(self.img_path)
        filename, ext = os.path.splitext(tail)
        new_tail = '{}.stl'.format(filename)
        new_path = os.path.join(head, new_tail)
        return new_path

    def get_pixel_gen(self):
        # reverse y-axis to fix image
        return (Pixel(img_arr=self.fixed_img_arr, img_height=self.height, img_width=self.width, x=x, y=y, dx=self.dx, dy=self.dy, dz=self.dz)
        for x in range(self.width) for y in range(self.height))

    @property
    def triangle_count(self):
        print("getting triangle count...")
        tri_count = 0
        for pixel in tqdm.tqdm(self.get_pixel_gen(), total=self.num_of_pixels):
            tri_count += len(pixel.triangles.values())

        return tri_count

    def make_stl(self):

        stl = mesh.Mesh(np.zeros(self.triangle_count, dtype=mesh.Mesh.dtype))

        i = -1
        for pixel in tqdm.tqdm(self.get_pixel_gen(), total=self.num_of_pixels):
            for triangle in pixel.triangles.values():
                i += 1
                for j in range(3):
                    stl.vectors[i][j] = triangle[j]

        # Write the mesh to file "cube.stl"
        stl.save(self.output_stl_path)


class Pixel:

    def __init__(self, img_arr, img_height, img_width, x, y, dx, dy, dz):
        self.img_arr = img_arr
        self.img_height, self.img_width = img_height, img_width
        self.dx, self.dy, self.dz = dx, dy, dz
        self.x = x
        self.y = y

        # self.z_scale = 1.0 / 25.5
        self.z = self.img_arr[y, x]

    def coord_transform(self, coordinate_tuple):
        x, y, z = coordinate_tuple
        new_x = x * self.dx
        new_y = (self.img_height - 1 - y) * self.dy
        new_z = z * self.dz

        return new_x, new_y, new_z

    @property
    def right_neighbor_z(self):
        return self.img_arr[self.y, self.x + 1]

    @property
    def bottom_neighbor_z(self):
        return self.img_arr[self.y + 1, self.x]

    @property
    def has_elevation_change_right(self):
        return self.z != self.right_neighbor_z

    @property
    def has_elevation_change_bottom(self):
        return self.z != self.bottom_neighbor_z

    @property
    def not_right_edge(self):
        return self.x < self.img_width - 1

    @property
    def not_bottom_edge(self):
        return self.y < self.img_height - 1

    @property
    def vertices(self):
        # do transformations here
        vertex_list = {
            'upper_left': self.coord_transform((self.x, self.y, self.z)),
            'upper_right': self.coord_transform((self.x + 1, self.y, self.z)),
            'lower_left': self.coord_transform((self.x, self.y + 1, self.z)),
            'lower_right': self.coord_transform((self.x + 1, self.y + 1, self.z)),
            'right_neighbor_upper_left': self.coord_transform((self.x + 1, self.y, self.right_neighbor_z)),
            'right_neighbor_lower_left': self.coord_transform((self.x + 1, self.y + 1, self.right_neighbor_z)),
            'bottom_neighbor_upper_left': self.coord_transform((self.x, self.y + 1, self.bottom_neighbor_z)),
            'bottom_neighbor_upper_right': self.coord_transform((self.x + 1, self.y + 1, self.bottom_neighbor_z))
        }

        return vertex_list

    @property
    def triangles(self):
        v = self.vertices

        triangles = {
            'top_1': (v['upper_left'], v['upper_right'], v['lower_left']),
            'top_2': (v['upper_right'], v['lower_left'], v['lower_right'])
        }

        # add right-side triangles if necessary
        if self.has_elevation_change_right and self.not_right_edge:
            triangles['right_1'] = (v['upper_right'], v['right_neighbor_upper_left'], v['lower_right'])
            triangles['right_2'] = (v['right_neighbor_upper_left'], v['lower_right'], v['right_neighbor_lower_left'])

        # add bottom-side triangles if necessary
        if self.has_elevation_change_bottom  and self.not_bottom_edge:
            triangles['bottom_1'] = (v['lower_left'], v['lower_right'], v['bottom_neighbor_upper_left'])
            triangles['bottom_2'] = (v['lower_right'], v['bottom_neighbor_upper_left'], v['bottom_neighbor_upper_right'])

        return triangles


if __name__ == '__main__':
    print("starting script...")

    input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\samus.jpg'
    PixelGroup(img_path=input_img_path).make_stl()

    # triang = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles=triangles)
    # plt.triplot(triang, marker="o")
    #
    # plt.show()

    print("done!")
