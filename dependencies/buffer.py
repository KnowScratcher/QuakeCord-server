import numpy as np

global buffer_x, buffer_y, buffer_z
buffer_x = {}
buffer_y = {}
buffer_z = {}
buffer_quake_x = {}
buffer_quake_y = {}
buffer_quake_z = {}
max_size = 2000

def get_buffer(station_id: str):
    if station_id in buffer_x:
        return np.array([buffer_x[station_id], buffer_y[station_id], buffer_z[station_id]]).T
    else:
        return np.array([]).reshape(0, 3)

def get_quake_buffer(station_id: str):
    if station_id in buffer_quake_x:
        return np.array([buffer_quake_x[station_id], buffer_quake_y[station_id], buffer_quake_z[station_id]]).T
    else:
        return np.array([]).reshape(0, 3)

def add_to_buffer(station_id: str, data: np.ndarray):
    """
    Adds new data to the buffers for each axis.

    Args:
        station_id (str): The ID of the station to which the data belongs.
        data (np.ndarray): New incoming data with shape (n_samples, 3) where each column corresponds to x, y, z axes.
    """
    global buffer_x, buffer_y, buffer_z, max_size
    if station_id not in buffer_x:
        buffer_x[station_id] = np.array(data[:, 0], dtype=np.float32)
        buffer_y[station_id] = np.array(data[:, 1], dtype=np.float32)
        buffer_z[station_id] = np.array(data[:, 2], dtype=np.float32)
    else:
        buffer_x[station_id] = np.concatenate((buffer_x[station_id], data[:, 0]))
        buffer_y[station_id] = np.concatenate((buffer_y[station_id], data[:, 1]))
        buffer_z[station_id] = np.concatenate((buffer_z[station_id], data[:, 2]))
    clean_buffer(station_id, max_size)
    return np.array([buffer_x[station_id], buffer_y[station_id], buffer_z[station_id]]).T

def add_to_quake_buffer(station_id: str, data: np.ndarray):
    """
    Adds new data to the quake buffers for each axis.

    Args:
        station_id (str): The ID of the station to which the data belongs.
        data (np.ndarray): New incoming data with shape (n_samples, 3) where each column corresponds to x, y, z axes.
    """
    global buffer_quake_x, buffer_quake_y, buffer_quake_z, max_size
    if station_id not in buffer_quake_x:
        buffer_quake_x[station_id] = np.array(data[:, 0], dtype=np.float32)
        buffer_quake_y[station_id] = np.array(data[:, 1], dtype=np.float32)
        buffer_quake_z[station_id] = np.array(data[:, 2], dtype=np.float32)
    else:
        buffer_quake_x[station_id] = np.concatenate((buffer_quake_x[station_id], data[:, 0]))
        buffer_quake_y[station_id] = np.concatenate((buffer_quake_y[station_id], data[:, 1]))
        buffer_quake_z[station_id] = np.concatenate((buffer_quake_z[station_id], data[:, 2]))
    clean_buffer(station_id, max_size)
    return np.array([buffer_quake_x[station_id], buffer_quake_y[station_id], buffer_quake_z[station_id]]).T

def reset_quake_buffer():
    """
    Resets the quake buffers for each axis.
    """
    global buffer_quake_x, buffer_quake_y, buffer_quake_z
    buffer_quake_x = {}
    buffer_quake_y = {}
    buffer_quake_z = {}

def clean_buffer(station_id: str, max_size: int):
    """
    Cleans the buffers to ensure they do not exceed the specified maximum size.

    Args:
        station_id (str): The ID of the station whose buffers are to be cleaned.
        max_size (int): The maximum allowed size for each buffer.
    """
    global buffer_x, buffer_y, buffer_z
    if station_id in buffer_x and len(buffer_x[station_id]) > max_size:
        buffer_x[station_id] = buffer_x[station_id][-max_size:]
    if station_id in buffer_y and len(buffer_y[station_id]) > max_size:
        buffer_y[station_id] = buffer_y[station_id][-max_size:]
    if station_id in buffer_z and len(buffer_z[station_id]) > max_size:
        buffer_z[station_id] = buffer_z[station_id][-max_size:]