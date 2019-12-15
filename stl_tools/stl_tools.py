from stl import mesh
from mpl_toolkits import mplot3d
from matplotlib import pyplot as plt
# import imageio
from PIL import Image
import numpy as np
import tqdm
# import matplotlib.tri as mtri


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

        self.img = Image.open(img_path).convert('LA')
        self.img.show()

        self.img_arr = np.asarray(self.img)[:, :, 0]

        self.height, self.width = self.img_arr.shape
        self.num_of_pixels = self.height * self.width

        # add extra row & column
        fixed_img_arr = np.append(self.img_arr, np.zeros(shape=(1, self.width)), axis=0)
        fixed_img_arr = np.append(fixed_img_arr, np.zeros(shape=(self.height + 1, 1)), axis=1)

        self.fixed_img_arr = fixed_img_arr

    def get_pixel_gen(self):
        return (Pixel(img_arr=self.fixed_img_arr, x=x, y=y) for x in range(self.width) for y in range(self.height))

    def make_stl(self):

        # emboss_depth = 100
        # emboss_width = 1000
        #
        # d_z = float(emboss_depth) / (img_data.max())
        # d_x = float(emboss_width) / width
        # d_y = d_x * height / width

        num_of_triangles = 6 * self.num_of_pixels
        cube = mesh.Mesh(np.zeros(num_of_triangles, dtype=mesh.Mesh.dtype))

        i = -1
        for pixel in tqdm.tqdm(self.get_pixel_gen(), total=self.num_of_pixels):
            for triangle in pixel.triangles.values():
                i += 1
                for j in range(3):
                    cube.vectors[i][j] = triangle[j]

        # Write the mesh to file "cube.stl"
        cube.save('output.stl')


class Pixel:

    def __init__(self, img_arr, x, y):
        self.img_arr = img_arr
        self.x = x
        self.y = y
        self.z = (1.0 / 25.5) * self.img_arr[y, x]

    @property
    def right_neighbor_z(self):
        return (1.0 / 25.5) * self.img_arr[self.y, self.x + 1]

    @property
    def bottom_neighbor_z(self):
        return (1.0 / 25.5) * self.img_arr[self.y + 1, self.x]

    @property
    def vertices(self):
        vertex_list = {
            'upper_left': (self.x, self.y, self.z),
            'upper_right': (self.x + 1, self.y, self.z),
            'lower_left': (self.x, self.y + 1, self.z),
            'lower_right': (self.x + 1, self.y + 1, self.z),
            'right_neighbor_upper_left': (self.x + 1, self.y, self.right_neighbor_z),
            'right_neighbor_lower_left': (self.x + 1, self.y + 1, self.right_neighbor_z),
            'bottom_neighbor_upper_left': (self.x, self.y + 1, self.bottom_neighbor_z),
            'bottom_neighbor_upper_right': (self.x + 1, self.y + 1, self.bottom_neighbor_z)
        }

        return vertex_list

    @property
    def triangles(self):
        v = self.vertices

        triangles = {
            'top_1': (v['upper_left'], v['upper_right'], v['lower_left']),
            'top_2': (v['upper_right'], v['lower_left'], v['lower_right']),

            'right_1': (v['upper_right'], v['right_neighbor_upper_left'], v['lower_right']),
            'right_2': (v['right_neighbor_upper_left'], v['lower_right'], v['right_neighbor_lower_left']),

            'bottom_1': (v['lower_left'], v['lower_right'], v['bottom_neighbor_upper_left']),
            'bottom_2': (v['lower_right'], v['bottom_neighbor_upper_left'], v['bottom_neighbor_upper_right']),
        }

        return triangles


if __name__ == '__main__':
    print("starting script...")

    input_img_path = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\samus2.png'
    PixelGroup(img_path=input_img_path).make_stl()

    # triang = mtri.Triangulation(xy[:, 0], xy[:, 1], triangles=triangles)
    # plt.triplot(triang, marker="o")
    #
    # plt.show()

    print("done!")
