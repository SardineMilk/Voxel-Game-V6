import numpy as np
from math import sin, cos, radians
import pygame
from pygame.locals import *
from pygame.math import *
from pygame import gfxdraw
"""
import profiler
profiler.profiler().start(True)
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
    speed = MOVE_SPEED * delta/1000
    camera_x, camera_y, camera_z = camera.position
    pitch, yaw, roll = radians(camera.pitch), radians(camera.yaw), radians(camera.roll)

    """
    movement_vector = Vector3(0, 0, 0)
    if keys[K_w]:  # Move forward
        movement_vector.z += 1
    if keys[K_s]:  # Move backward
        movement_vector.z -= 1
    if keys[K_d]:  # Strafe left
        movement_vector.x += 1
    if keys[K_a]:  # Strafe right
        movement_vector.x -= 1
    if keys[K_SPACE]:  # Move up
        movement_vector.y += 1
    if keys[K_LSHIFT]:  # Move down
        movement_vector.y -= 1
    """

    if keys[K_w]:  # Move forward
        camera_x -= sin(yaw) * speed
        camera_z -= cos(yaw) * speed
    if keys[K_s]:  # Move backward
        camera_x += sin(yaw) * speed
        camera_z += cos(yaw) * speed
    if keys[K_d]:  # Strafe left
        camera_x -= cos(yaw) * speed
        camera_z += sin(yaw) * speed
    if keys[K_a]:  # Strafe right
        camera_x += cos(yaw) * speed
        camera_z -= sin(yaw) * speed
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

    for face_index, face in enumerate(FACES):
        projected_face = ()  # Pygame polygons need a tuple instead of a list
        visible = check_visibility(face_index, voxel_position)
        if visible:
            for vertex_index in face:
                x, y, z = VERTICES[vertex_index]
                vertex = Vector3(float(x), float(y), float(z))
                vertex += voxel_position
                vertex += camera.position

                vertex = rotate_vertex(vertex, camera.yaw, camera.pitch, camera.roll)

                # Frustum Culling - Don't render if behind camera
                if vertex[2] < FRUSTUM_TOLERANCE:  # vertex[2] is the z_pos
                    break

                x, y = project_vertex(vertex)
                # Concatenate the projected vertex to the face tuple
                projected_face += ((x, y),)

        if len(projected_face) == 4:  # If all 4 vertices are visible
            # Fetch the voxel colour.
            # Doing it here instead of at the start allows for more flexible shading i.e. voxel position based
            voxel_colour = voxel_types[voxel_type - 1]  # -1 because 0 is air
            r, g, b = FACE_NORMALS[face_index]
            r, g, b = (r+1)*127.75, (g+1)*127.75, (b+1)*127.75
            voxel_colour = r, g, b
            processed_face_data = projected_face, voxel_colour
            processed_voxel.append(processed_face_data)

    return processed_voxel


def project_vertex(vertex):
    x, y, z = vertex
    x_2d = (FOCAL_LENGTH * (x / z) + 1) * centre_x
    y_2d = (FOCAL_LENGTH * (y / z) + 1) * centre_y

    return int(x_2d), int(y_2d)


def rotate_vertex(vertex, yaw, pitch, roll):
    # Rotate Yaw - Y
    vertex = vertex.rotate(-yaw, Vector3(0, 1, 0))
    # Rotate Pitch - X
    vertex = vertex.rotate(pitch, Vector3(1, 0, 0))
    # Rotate Roll - Z
    vertex = vertex.rotate(roll, Vector3(0, 0, 1))

    return vertex


def check_visibility(face_index, voxel_pos):
    normal = FACE_NORMALS[face_index]  # This is incredibly slow to calculate, so it's baked instead

    # Interior Face Culling - Cull anything facing another voxel
    check_x, check_y, check_z = voxel_pos - normal
    if voxels[check_x, check_y, check_z] != 0:
        return False

    # Backface culling - If it's facing away from the camera, cull it
    relative_pos = voxel_pos + camera.position + (0.5, 0.5, 0.5)
    camera_dir = np.array(VERTICES[face_index]) - relative_pos
    face_to_camera = np.dot(normal, camera_dir)  # Dot product of the face normal to the camera
    if face_to_camera > BACKFACE_TOLERANCE:
        return False

    return True


def clamp(n, minn, maxn):
    return max(minn, min(n, maxn))


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
    (0, 1, 2, 3),  # Front face
    (5, 4, 7, 6),  # Back face
    (4, 0, 3, 7),  # Left face
    (1, 5, 6, 2),  # Right face
    (4, 5, 1, 0),  # Top face
    (3, 2, 6, 7),  # Bottom face
]
# Bake face normals, so they aren't calculated each frame
FACE_NORMALS = [
    (0, 0, 1),
    (0, 0, -1),
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
]

voxel_types = [
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 0),
]

# Setup pygame and display
pygame.init()
WIDTH, HEIGHT = 800, 800  # Base resolution for display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
centre_x, centre_y = screen.get_width()/2, screen.get_height()/2
clock = pygame.time.Clock()
time = 0

BACKFACE_TOLERANCE = -0.5
FRUSTUM_TOLERANCE = 0.5
FOCAL_LENGTH = 1
MAX_FPS = 120
MOUSE_SENSITIVITY = 0.25
MOVE_SPEED = 5

camera = Camera((0.0, 1.0, 5.0), 0, 0, 0)
voxels = np.zeros((16, 16, 16), dtype=int)

# World generation
for i in range(0, 15):
    for j in range(0, 15):
        for k in range(0, 15):
            if j <= 2:
                voxels[i, j, k] = (i+j+k) % 3 + 1

# Mouse lock
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)

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

    if keys[K_ESCAPE]:
        running = False

    # Time and frame rate
    current_time = pygame.time.get_ticks()
    delta = current_time - time
    time = current_time

    camera = move_camera()
    print(camera.position)

    # Process the voxels
    filtered_voxels = np.argwhere(voxels != 0)  # Array of the indices of non-zero voxels
    sorted_voxels = sort_voxels(filtered_voxels, camera.position)  # Sorted based on distance from camera

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
