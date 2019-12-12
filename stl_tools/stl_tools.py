from stl import mesh
from mpl_toolkits import mplot3d
from matplotlib import pyplot as plt
# import imageio
from PIL import Image
import numpy as np
import tqdm


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


if __name__ == '__main__':
    print("starting script...")

    stl_file = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\HalfDonut.stl'
    png_file = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\mg_logo.gif'
    mcdonalds = r'C:\Users\James\PycharmProjects\3D_printing\stl_tools\mario.jpg'
    # show_render(stl_file)

    # im = imageio.imread(png_file)




    img = Image.open(mcdonalds).convert('LA')
    # img_data = np.asarray(img)[:, :, 0]
    img_data = np.asarray(img)[:, :, 0]

    # print(im.shape)
    height, width = img_data.shape
    num_of_pixels = height * width
    emboss_depth = 100
    emboss_width = 1000

    d_z = float(emboss_depth)/(img_data.max())
    d_x = float(emboss_width)/width
    d_y = d_x * height / width

    # pixels = []
    number_of_verticies = 4*width*height
    vertices = np.zeros(shape=(number_of_verticies, 3), dtype=np.int8)
    for y in tqdm.tqdm(range(height)):
        for x in range(width):
            z = img_data[y, x]

            pixel_num = 4 * y * width + 4 * x
            vertices[pixel_num + 0] = x, y, z  # ul
            vertices[pixel_num + 1] = x + 1, y, z  # ur
            vertices[pixel_num + 2] = x, y + 1, z  # ll
            vertices[pixel_num + 3] = x + 1, y + 1, z  # lr


    # iterate over pixels
    num_of_triangles = 6 * num_of_pixels
    triangles = np.empty(shape=(num_of_triangles, 3), dtype=np.int64)
    for i in tqdm.tqdm(range(num_of_pixels)):
        vertex_index = i * 4
        triangle_index = i * 6

        # top
        top_1 = [0, 1, 2]
        top_2 = [1, 2, 3]

        # right
        right_1 = [1, 3, 0 + 4]
        right_2 = [3, 4 + 0, 4 + 2]

        # bottom
        bottom_1 = [2, 3, 4 + 0]
        bottom_2 = [3, 4 + 0, 4 + 1]



        for j, arr in enumerate([top_1, top_2, right_1, right_2, bottom_1, bottom_2]):
            triangles[triangle_index+j] = [x + vertex_index for x in arr]

    # Create the mesh
    cube = mesh.Mesh(np.zeros(triangles.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in tqdm.tqdm(enumerate(triangles[:-100])):
        for j in range(3):
            cube.vectors[i][j] = vertices[f[j], :]

    # Write the mesh to file "cube.stl"
    cube.save('cube.stl')

    # plt.imshow(img)
    # plt.show(block=True)

    print("done!")
