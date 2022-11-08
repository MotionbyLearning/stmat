import dask
import numpy as np
import xarray as xr
import dask.array as da
import datetime

# Example: https://docs.dask.org/en/stable/array-creation.html
def read_stack(slc_files, shape, vlabel, dtype=np.float16, blocksize=5):

    coords = {
        "azimuth": range(shape[0]),
        "range": range(shape[1]),
        "time": range(len(slc_files)),
    }
    stack = xr.Dataset(coords=coords)
    
    slcs = None
    for f_slc in slc_files:
        if slcs is None:
            slcs = read_slc(f_slc, shape, dtype, blocksize).reshape((shape[0],shape[1],1))
        else:
            slc = read_slc(f_slc, shape, dtype, blocksize).reshape((shape[0],shape[1],1))
            slcs = da.concatenate([slcs, slc], axis=2)
    
    stack = stack.assign({vlabel: (("azimuth","range","time"), slcs)})

    return stack


def read_slc(filename_or_obj, shape, dtype, blocksize):
    
    slc = _mmap_dask_array(filename=filename_or_obj, shape=shape, dtype=dtype, blocksize=blocksize)

    return slc


def _mmap_dask_array(filename, shape, dtype, blocksize):
    """
    Create a Dask array from raw binary data in :code:`filename`
    by memory mapping.

    This method is particularly effective if the file is already
    in the file system cache and if arbitrary smaller subsets are
    to be extracted from the Dask array without optimizing its
    chunking scheme.

    It may perform poorly on Windows if the file is not in the file
    system cache. On Linux it performs well under most circumstances.

    Parameters
    ----------

    filename : str
    shape : tuple
        Total shape of the data in the file
    dtype:
        NumPy dtype of the data in the file
    blocksize : int, optional
        Chunk size for the outermost axis. The other axes remain unchunked.

    Returns
    -------

    dask.array.Array
        Dask array matching :code:`shape` and :code:`dtype`, backed by
        memory-mapped chunks.
    """
    load = dask.delayed(_mmap_load_chunk)
    chunks = []
    for index in range(0, shape[0], blocksize):
        # Truncate the last chunk if necessary
        chunk_size = min(blocksize, shape[0] - index)
        chunk = dask.array.from_delayed(
            load(
                filename,
                shape=shape,
                dtype=dtype,
                sl=slice(index, index + chunk_size),
            ),
            shape=(chunk_size,) + shape[1:],
            dtype=dtype,
        )
        chunks.append(chunk)
    return da.concatenate(chunks, axis=0)


def _mmap_load_chunk(self, filename, shape, dtype, sl):
    """
    Memory map the given file with overall shape and dtype and return a slice
    specified by :code:`sl`.

    Parameters
    ----------

    filename : str
    shape : tuple
        Total shape of the data in the file
    dtype:
        NumPy dtype of the data in the file
    sl:
        Object that can be used for indexing or slicing a NumPy array to
        extract a chunk

    Returns
    -------

    numpy.memmap or numpy.ndarray
        View into memory map created by indexing with :code:`sl`,
        or NumPy ndarray in case no view can be created using :code:`sl`.
    """
    data = np.memmap(filename, mode="r", shape=shape, dtype=dtype)
    return data[sl]
