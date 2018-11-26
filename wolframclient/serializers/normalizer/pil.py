# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import sys
from wolframclient.utils import six 
from wolframclient.utils.api import PIL, numpy
from wolframclient.language import wl
""" Serialize a given :class:`PIL.Image` into a Wolfram Language image.

    This method first tries to extract the data and relevant information about the image,
    and reconstruct it using :wl:`Image` constructor. This is the most efficient way to
    proceed, but is not guaranteed to work all the time. Only some pixel representations
    are supported, fortunatelly the most common ones.

    When the internal PIL representation does not correspond to one of the Wolfram Language,
    the image is converted to its format, if specified, or ultimatelly to PNG. This may fail,
    in which case an exception is raised and there is nothing more we can do.

    In theory we could represent any image, but due to :func:`~PIL.Image.convert()` behaviour 
    we can't. This function is not converting, but naively casts to a given type without rescaling.
    e.g. int32 values above 255 converted to bytes become 255. We can't cast properly from 'I' mode
    since some format are using 'I' for say 'I;16' (int16) and the rawmode is not always accessible.
    
    See bug in convert: https://github.com/python-pillow/Pillow/issues/3159
"""

MODE_MAPPING = {
    # mode  : (type, colorspace, interleaving)
    "1"     : ("Bit", None, True),
    "L"     : ("Byte", "Grayscale", True),
    "RGB"   : ("Byte", "RGB", True),
    "CMYK"  : ("Byte", "CMYK", True),
    "LAB"   : ("Byte", "LAB", True),
    "F"     : ("Real32", None, True),
    "RGBA"  : ("Byte", "RGB", True),
    "HSV"   : ("Byte", "HSB", True)
}
SYS_IS_LE = sys.byteorder == 'little'
DTYPE_BOOL = numpy.dtype('bool')

def normalize_array(array):
    # big endian
    endianness = array.dtype.byteorder
    # Ensure little endian
    if endianness == '>' or (endianness == '=' and not SYS_IS_LE):
        array.byteswap().newbyteorder()
    if array.dtype == DTYPE_BOOL:
        array = array.astype('<u1')
    return array

def update_dispatch(dispatch):
    @dispatch.multi(PIL.Image)
    def normalizer(self, img):
        # some PIL mode are directly mapped to WL ones. Best case fast (de)serialization.
        mode = img.mode
        if mode in MODE_MAPPING:
            data=normalize_array(numpy.array(img))
            wl_data_type, colorspace, interleaving = MODE_MAPPING[mode]

            return self.normalize(
                wl.Image(data, wl_data_type, ColorSpace=colorspace or wl.Automatic, Interleaving=interleaving)
            )
        else:
            # try to use format and import/export, may fail during save() and raise exception.
            stream = six.BytesIO()
            img_format=img.format or "PNG"
            try:
                img.save(stream, format=img_format)
            except KeyError:
                raise NotImplementedError('Format %s is not supported.' % img_format)
            return self.serialize_function(
                    self.serialize_symbol(b'ImportByteArray'),
                    (
                        self.serialize_bytes(stream.getvalue()),
                        self.serialize_string(img_format)
                    )
                )
