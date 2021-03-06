#!/usr/bin/env python

import os
import struct
import numpy as np
import hashlib

class Header(object):
    def __init__(self, filehandle):
        self.packed_format = 'I'*19
        self.packed_size = 19 * 4
        self.fieldnames = [
            'filetype', 'nframes', 'w', 'h', 'ss', '[ul]', '[ur]',
            '[br]', '[bl]', 'probe', 'txf', 'sf', 'dr', 'ld', 'extra'
        ]
        packed_hdr = filehandle.read(self.packed_size)
        hfields = struct.unpack(self.packed_format, packed_hdr)
        idx = 0
        for field in self.fieldnames:
            if field.startswith('['):
                field = field.replace('[','').replace(']','')
                setattr(self, field, [hfields[idx], hfields[idx+1]])
                idx += 2
            else:
                setattr(self, field, hfields[idx])
                idx += 1

class BprReader:
    def __init__(self, filename, checksum=False):
        self.filename = os.path.abspath(filename)
        self._fhandle = None
        self.open()
        self.header = Header(self._fhandle)
        # TODO: when we have more image readers other than bpr, they all should
        # have attributes for the image height and width, number of frames, and
        # data type (i.e. the numeric type of the data values), and we make
        # these attributes of the reader object itself; they won't necessarily
        # be found in the header.
        self.h = self.header.h
        self.w = self.header.w
        self.nframes = self.header.nframes
        if self.header.filetype == 2:
            self.dtype = np.uint8
        else:
            msg = "Unexpected filetype! Expected 2 and got {filetype:d}"
            raise ValueError(msg.format(filetype=self.header.filetype))
        # these data_fmt and framesize values are specific to .bpr
        self.data_fmt = 'B' * (self.header.h * self.header.w)
        self.framesize = 1 * (self.header.h * self.header.w)
        self.csums = [None] * self.header.nframes
        if checksum:
            for idx in range(self.header.nframes):
                print("working on {:d}".format(idx))
                data = self.get_frame()
                csum = hashlib.sha1(data.copy(order="c")).hexdigest()
                if csum in self.csums:
                    "Frame {:d} is a duplicate!".format(idx)
                self.csums[idx] = csum
        self._fhandle.seek(self.header.packed_size)
        self._cursor = self._fhandle.tell()
        self.close()

    def __iter__(self):
        return self

    def next(self):
        '''Get the next image frame.'''
        if self._fhandle is None:
            self.open()
        try:
            self._fhandle.seek(self._cursor)
            packed_data = self._fhandle.read(self.framesize)
            data = np.array(struct.unpack(self.data_fmt, packed_data))
        except struct.error:   # ran out of data to unpack()
            raise StopIteration
        self._cursor = self._fhandle.tell()
        return data.reshape([self.header.w, self.header.h]).T
 
    def get_frame(self, idx=None):
        '''Get the image frame specified by idx. Do not advance the read location of _fhandle.'''
        if self._fhandle is None:
            self.open()
        self._fhandle.seek(self.header.packed_size + (idx * self.framesize))
        packed_data = self._fhandle.read(self.framesize)
        self._fhandle.seek(self._cursor)
        data = np.array(struct.unpack(self.data_fmt, packed_data))
        return data.reshape([self.header.w, self.header.h]).T

    def open(self):
        self._fhandle = open(self.filename, 'rb')

    def close(self):
        try:
            self._fhandle.close()
            self._fhandle = None
        except Exception as e:
            raise e
