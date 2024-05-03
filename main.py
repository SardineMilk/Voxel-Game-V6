import numpy as np
from math import sin, cos, radians
import pygame
import pygame.freetype
from pygame.locals import *
from pygame.math import *
from pygame import gfxdraw
from random import randint

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


def move_camera():
    speed = MOVE_SPEED * delta/1000
    camera_x, camera_y, camera_z = camera.position
    pitch, yaw, roll = radians(camera.pitch), radians(camera.yaw), radians(camera.roll)

    if keys[K_w]:  # Move forward
        camera_x += sin(yaw) * speed
        camera_z += cos(yaw) * speed
    if keys[K_s]:  # Move backward
        camera_x -= sin(yaw) * speed
        camera_z -= cos(yaw) * speed
    if keys[K_d]:  # Strafe left
        camera_x += cos(yaw) * speed
        camera_z -= sin(yaw) * speed
    if keys[K_a]:  # Strafe right
        camera_x -= cos(yaw) * speed
        camera_z += sin(yaw) * speed
    if keys[K_SPACE]:  # Move up
        camera_y -= speed
    if keys[K_LSHIFT]:  # Move down
        camera_y += speed

    camera.position = (camera_x, camera_y, camera_z)

    return camera


def sort_voxels(input_array, point):
    # Sort the array based on distance from point
    distances = np.linalg.norm(input_array - point, axis=1)  # The docs are unreadable but its just pythagoras
    distances = np.argsort(distances)[::-1]  # Reverse sort list and return indices - Furthest get drawn first
    output_array = input_array[distances]  # Get the sorted array from the distances
    return output_array


def process_face(face):
    position, index = face
    voxel_x, voxel_y, voxel_z = position
    voxel_type = voxels[voxel_x, voxel_y, voxel_z]
    face = FACES[index]

    projected_face = ()  # Pygame polygons need a tuple instead of a list
    visible = check_visibility(index, position)
    if visible:
        for vertex_index in face:
            x, y, z = VERTICES[vertex_index]
            vertex = Vector3(float(x), float(y), float(z))
            vertex += position
            vertex -= camera.position  # subtract because we are moving the world relative to the camera

            # Rotate Yaw - Y
            vertex = vertex.rotate(-camera.yaw, Vector3(0, 1, 0))
            # Rotate Pitch - X
            vertex = vertex.rotate(camera.pitch, Vector3(1, 0, 0))
            # Rotate Roll - Z
            # vertex = vertex.rotate(camera.roll, Vector3(0, 0, 1))

            # Frustum Culling - Don't render if behind camera
            if vertex[2] <= FRUSTUM_TOLERANCE:  # vertex[2] is the z_pos
                break

            x, y = project_vertex(vertex)
            # Concatenate the projected vertex to the face tuple
            projected_face += ((x, y),)

    if len(projected_face) == 4:  # If all 4 vertices are visible
        # Fetch the voxel colour.
        # Doing it here instead of at the start allows for more flexible shading i.e. voxel position based
        voxel_colour = voxel_types[voxel_type - 1]  # -1 because 0 is air

        return projected_face, voxel_colour


def project_vertex(vertex):
    x, y, z = vertex
    x_2d = ((x / z) + 1) * centre_x
    y_2d = ((y / z) + 1) * centre_y

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
    # Backface culling - If it's facing away from the camera, cull it
    normal = FACE_NORMALS[face_index]  # This is incredibly slow to calculate, so it's baked instead
    relative_pos = voxel_pos + (0.5, 0.5, 0.5) - camera.position

    # Dot product of the face normal to the camera vector
    # If this is positive, they are pointing in roughly the same direction - <90 degrees
    # If it's negative, they are pointing roughly away from each other - >90 degrees
    # 3blue1brown has a wonderful linear algebra video explaining this: https://www.youtube.com/watch?v=LyGKycYT2v0
    face_to_camera = np.dot(normal, relative_pos)

    # Use a slight bias to prevent shapes being culled incorrectly
    is_visible = face_to_camera <= -0.5

    return is_visible


def construct_mesh(input_voxels):
    filtered_voxels = np.argwhere(input_voxels != 0)  # Array of the indices of non-zero voxels
    sorted_voxels = sort_voxels(filtered_voxels, camera.position)  # Sorted based on distance from camera

    mesh = []
    for voxel_pos in sorted_voxels:
        for face_index, face in enumerate(FACES):
            face_normal = FACE_NORMALS[face_index]

            check_x, check_y, check_z = voxel_pos + face_normal
            if voxels[check_x, check_y, check_z] == 0:
                mesh.append((voxel_pos, face_index))

    # mesh = greedy_mesh(mesh)

    return mesh


def greedy_mesh(mesh):
    processed_mesh = []
    for face_data in mesh:
        voxel_pos, face_index = face_data
        processed_mesh.append((voxel_pos, face_index, 1, 1))    # voxel_pos, face_index, width, height

    return processed_mesh


def clamp(n, minn, maxn):
    return max(minn, min(n, maxn))


# Position of each vertex relative to the voxel's position (top front left)
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
    (4, 5, 6, 7),  # Back face
    (4, 0, 3, 7),  # Left face
    (1, 5, 6, 2),  # Right face
    (4, 5, 1, 0),  # Top face
    (3, 2, 6, 7),  # Bottom face
]
# Bake face normals, so they aren't calculated each frame
FACE_NORMALS = [
    (0, 0, -1),
    (0, 0, 1),
    (-1, 0, 0),
    (1, 0, 0),
    (0, -1, 0),
    (0, 1, 0),
]
# List of available voxel colour
# At some point im going to turn this into a file
voxel_types = [
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 0),
]

# Constants
WIDTH, HEIGHT = 800, 800  # Base resolution for display
FRUSTUM_TOLERANCE = 0.25
MAX_FPS = 9999
MOUSE_SENSITIVITY = 0.25
MOVE_SPEED = 5

# Setup pygame and display
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
centre_x, centre_y = screen.get_width()/2, screen.get_height()/2
clock = pygame.time.Clock()
time = 0

# Setup text display
font = pygame.freetype.Font(pygame.font.get_default_font(), 24)

frames = 0
camera = Camera(Vector3(0.0, -5.0, 0.0), 0, 0, 0)
voxels = np.zeros((16, 16, 16), dtype=int)
geometry_changed = True

voxels_mesh = construct_mesh(voxels)

# World generation
for i in range(0, 15):
    for j in range(0, 15):
        for k in range(0, 15):
            if j < 5:
                voxels[i, j, k] = (i+j+k) % 3 + 1
                # voxels[i, j, k] = randint(0, 3)

# Mouse lock
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)

running = True
while running:
    frames += 1
    # Player logic
    for event in pygame.event.get():  # Movement breaks without this for some reason
        if event.type == MOUSEMOTION:
            mouse_dx, mouse_dy = event.rel
            camera.yaw += mouse_dx * MOUSE_SENSITIVITY
            camera.pitch += mouse_dy * MOUSE_SENSITIVITY
            camera.pitch = clamp(camera.pitch, -90, 90)  # Clamp camera pitch to directly up and down
    keys = pygame.key.get_pressed()

    if keys[K_ESCAPE]:
        running = False

    if keys[K_r]:
        for i in range(0, 15):
            for j in range(0, 15):
                for k in range(0, 15):
                    voxels[i, j, k] = randint(1, 3)
                    geometry_changed = True

    # Time and frame rate
    current_time = pygame.time.get_ticks()
    delta = current_time - time
    time = current_time
    fps = str(round(1000/delta, 2))

    camera = move_camera()

    # Construct the mesh
    if geometry_changed:
        voxels_mesh = construct_mesh(voxels)
        geometry_changed = False

    # Process the voxels
    processed_faces = [process_face(face_data) for face_data in voxels_mesh]  # List of quads and colours that must be drawn
    processed_faces = filter(None, processed_faces)

    # Render
    screen.fill((32, 32, 32))
    for face_data in processed_faces:
        shape, colour = face_data
        pygame.gfxdraw.filled_polygon(screen, shape, colour)
        pygame.gfxdraw.aapolygon(screen, shape, (127, 127, 127))

    # Display fps
    text_surface = font.render_to(screen, (1, 1), fps,(255, 255, 255))

    pygame.display.flip()
    clock.tick(MAX_FPS)

pygame.quit()
