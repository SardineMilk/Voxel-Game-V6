import numpy as np
from math import sin, cos, radians
import pygame
from pygame.locals import *
from pygame import gfxdraw
"""

from pygame.math import *
"""


class Camera:
    def __init__(self, camera_position, camera_yaw, camera_pitch, camera_roll):
        self.position = camera_position
        self.yaw = camera_yaw
        self.pitch = camera_pitch
        self.roll = camera_roll


class Voxel:
    def __init__(self, voxel_pos, voxel_type):
        self.pos = voxel_pos
        self.type = voxel_type


def move_camera():
    speed = 0.05
    camera_x, camera_y, camera_z = camera.position

    if keys[K_w]:  # Move forward
        camera_x -= sin(camera.yaw) * speed
        camera_z -= cos(camera.yaw) * speed
    if keys[K_s]:  # Move backward
        camera_x += sin(camera.yaw) * speed
        camera_z += cos(camera.yaw) * speed
    if keys[K_d]:  # Strafe left
        camera_x -= cos(camera.yaw) * speed
        camera_z += sin(camera.yaw) * speed
    if keys[K_a]:  # Strafe right
        camera_x += cos(camera.yaw) * speed
        camera_z -= sin(camera.yaw) * speed
    if keys[K_SPACE]:  # Move up
        camera_y += speed
    if keys[K_LSHIFT]:  # Move down
        camera_y -= speed

    camera.position = (camera_x, camera_y, camera_z)

    return camera


def sort_voxels(input_array, point):
    # Sort the array based on distance from point
    distances = np.linalg.norm(input_array + point, axis=1)  # Basically just pythagoras
    distances = np.argsort(distances)[::-1]  # Reverse sort the list
    output_array = input_array[distances]  # Get the sorted array from the distances
    return output_array


def process_voxel(voxel_position):
    # Keep decoupled from pygame for future multiprocessing
    voxel_x, voxel_y, voxel_z = voxel_position
    voxel_type = voxels[voxel_x, voxel_y, voxel_z]
    processed_voxel = []

    processed_vertices = []
    for vertex in VERTICES:
        x, y, z = vertex
        processed_vertex = float(x), float(y), float(z)
        processed_vertex += voxel_position
        processed_vertex += camera.position
        processed_vertex = rotate_vertex(processed_vertex, camera.pitch, camera.yaw, camera.roll)

        processed_vertices.append(processed_vertex)

    for i, face in enumerate(FACES):
        projected_face = ()  # Pygame polygons need a tuple instead of a list
        visible = check_visibility(i, voxel_position)
        if visible:
            for vertex_index in face:
                vertex = processed_vertices[vertex_index]
                # Frustum Culling - Don't render if behind camera
                if vertex[2] < FRUSTUM_TOLERANCE:  # vertex[2] is the z_pos
                    break

                x, y = project_vertex(vertex)
                # Concatenate the projected vertex to the face tuple
                projected_face += ((x, y),)

        if len(projected_face) == 4:  # If all 4 vertices are visible
            # Fetch the voxel colour. Doing it here allows for more flexible shading i.e. voxel position based
            voxel_colour = voxel_types[voxel_type - 1]  # -1 because 0 is air
            processed_face_data = projected_face, voxel_colour
            processed_voxel.append(processed_face_data)

    return processed_voxel


def rotate_vertex(point, pitch, yaw, roll):
    # This is done manually to decouple the voxel processing from pygame
    # Vector rotation with pygame would be faster, but multiprocessing makes up for it
    x, y, z = point

    # Store the trig for efficiency
    cos_pitch, sin_pitch = cos(pitch), sin(pitch)
    cos_yaw, sin_yaw = cos(-yaw), sin(-yaw)
    cos_roll, sin_roll = cos(roll), sin(roll)

    # Apply yaw rotation - y-axis
    x_yaw = x * cos_yaw + z * sin_yaw
    y_yaw = y
    z_yaw = -x * sin_yaw + z * cos_yaw

    # Apply pitch rotation - x-axis
    x_pitch = x_yaw
    y_pitch = y_yaw * cos_pitch - z_yaw * sin_pitch
    z_pitch = y_yaw * sin_pitch + z_yaw * cos_pitch

    # Apply roll rotation - z-axis
    x_roll = x_pitch * cos_roll - y_pitch * sin_roll
    y_roll = x_pitch * sin_roll + y_pitch * cos_roll
    z_roll = z_pitch

    return x_roll, y_roll, z_roll


def project_vertex(vertex):
    x, y, z = vertex
    x_2d = (FOCAL_LENGTH * (x / z) + 1) * centre_x
    y_2d = (FOCAL_LENGTH * (y / z) + 1) * centre_y

    return int(x_2d), int(y_2d)


def check_visibility(face_index, voxel_pos):
    current_face = FACES[face_index]
    normal = FACE_NORMALS[face_index]  # This is incredibly slow to calculate, so it's baked instead

    # Interior Face Culling - Cull anything facing another voxel
    check_x, check_y, check_z = voxel_pos - normal
    if voxels[check_x, check_y, check_z] != 0:
        return False

    # Backface culling - If it's facing away from the camera, cull it
    camera_dir = np.array(VERTICES[current_face[0]]) - voxel_pos - camera.position
    face_to_camera = np.dot(normal, camera_dir)  # Dot product of the face normal to the camera
    if face_to_camera > BACKFACE_TOLERANCE:
        return False

    return True


def clamp(n, minn, maxn):
    return min(maxn, max(n, minn))


# Position of each vertex relative to the voxel's position
VERTICES = [
    (0, 0, 0),
    (1, 0, 0),
    (1, 1, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 0, 1),
    (1, 1, 1),
    (0, 1, 1),
]
# Index into the vertex array
FACES = [
    (5, 4, 7, 6),  # Front face
    (4, 0, 3, 7),  # Right face
    (0, 1, 2, 3),  # Back face
    (1, 5, 6, 2),  # Left face
    (4, 5, 1, 0),  # Bottom face
    (3, 2, 6, 7),  # Top face
]
# Bake face normals, so they aren't calculated each frame
FACE_NORMALS = [
    (0, 0, -1),
    (1, 0, 0),
    (0, 0, 1),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0)
]

voxel_types = [
    (0, 255, 255),
    (255, 0, 255),
]

# Setup pygame and display
pygame.init()
WIDTH, HEIGHT = 800, 800  # Base resolution for display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
centre_x, centre_y = screen.get_width()/2, screen.get_height()/2
clock = pygame.time.Clock()

BACKFACE_TOLERANCE = -0.2
FRUSTUM_TOLERANCE = 0.5
FOCAL_LENGTH = 1
MAX_FPS = 60
MOUSE_SENSITIVITY = radians(0.25)

camera = Camera((0.0, 1.0, 5.0), 0, 0, 0)
voxels = np.zeros((16, 16, 16), dtype=int)

voxels[0, 0, 0] = 1
voxels[0, 1, 0] = 2
voxels[1, 2, 3] = 2

running = True
while running:
    # Player logic
    for event in pygame.event.get():  # Movement breaks without this for some reason
        if event.type == MOUSEMOTION:
            mouse_dx, mouse_dy = event.rel
            camera.yaw += mouse_dx * MOUSE_SENSITIVITY
            camera.pitch += mouse_dy * MOUSE_SENSITIVITY
            camera.pitch = clamp(camera.pitch, -90, 90)  # Clamp camera pitch within -89 to 89 degrees
    keys = pygame.key.get_pressed()
    camera = move_camera()

    pygame.mouse.set_visible(False)
    pygame.mouse.set_pos(centre_x, centre_y)
    pygame.event.set_grab(True)

    # Process the voxels
    filtered_voxels = np.argwhere(voxels != 0)  # Array of the indices of non-zero voxels
    sorted_voxels = sort_voxels(filtered_voxels, camera.position)  # filtered_voxels, sorted based on distance from camera
    processed_voxels = [process_voxel(pos) for pos in sorted_voxels]  # List of quads and colours that must be drawn

    # Render
    screen.fill((0, 0, 0))
    for voxel in processed_voxels:
        for quad in voxel:
            shape, colour = quad
            pygame.gfxdraw.filled_polygon(screen, shape, colour)
            pygame.gfxdraw.aapolygon(screen, shape, (255, 255, 255))

    pygame.display.flip()
    clock.tick(MAX_FPS)

pygame.quit()
