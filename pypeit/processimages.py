# Module for Processing Images, e.g. bias frames, arc frames

from __future__ import absolute_import, division, print_function

import inspect
import numpy as np
import os

#from importlib import reload

from astropy.io import fits

from pypeit import msgs
from pypeit import ginga
from pypeit.core import combine
from pypeit.core import procimg
from pypeit.core import flat
from pypeit.core import parse

from pypeit.par import pypeitpar

from pypeit.spectrographs.util import load_spectrograph

from pypeit import debugger

class ProcessImages(object):
    """
    Base class to guide image loading and processing.

    Args:
        spectrograph (:obj:`str`,
        :class:`pypeit.spectrographs.spectrograph.Spectrograph`):
            The spectrograph from which the data was taken.  Must be
            provided as a string that can be interpreted by
            :func:`pypeit.spectrographs.util.load_spectrograph` or a
            preconstructed instance of
            :class:`pypeit.spectrographs.spectrograph.Spectrograph`.
        files (:obj:`str`, :obj:`list`):
            One or more files to read and process.
        det (:obj:`int`, optional):
            The 1-indexed number of the detector.  Default is 1.
        par (:class:`pypeit.par.pypeitpar.ProcessImagesPar`, optional):
            Parameters that dictate the processing of the images.  See
            :class:`pypeit.par.pypeitpar.ProcessImagesPar` for the
            defaults.
        binning (:obj:`list`, optional):
            Binning of the relevant images in each file provided as a
            string.  Will be parsed into spatial and spectral binning
            using :func:`pypeit.core.parse.parse_binning`.  If None,
            determined from the header of each file.

    Attributes:
        files (:obj:`list`):
            The list of files to reduce. List can be empty.
        spectrograph
        (:class:`pypeit.spectrographs.spectrograph.Spectrograph`):
            The spectrograph used to take the data.
        det (:obj:`int`):
            Detector to process
        frametype (:obj:`str`):
            Class attribute that is overwritten by derived classes.
        stack (:obj:`numpy.ndarray`):
        steps (list):
        raw_images (list):
        headers (list):
        proc_images (:obj:`numpy.ndarray`):
            3D array of processed, individual images
        datasec (list):
            List of **slice** objects that select the data section from
            the images.
        oscansec (list):
            List of **slice** objects that select the overscan section
            from the images.

    Raises:
        TypeError:
            Raised if the spectrograph is not a :obj:`str` or
            :class:`Spectrograph`.
    """

    # TODO: add a utility function which acts as a wrapper for this
    # class, and simply takes a filename, and returns the image and the
    # classor something, i.e.
    #
    # class = pypeit_proc(filename, biasfile = biasfile, pixflatfile=pixflatfile,
    #                     illumflatfile=illumflatfile)
    #
    # or maybe it should return the image and the class?

    # Class attribute is unknown.  Will be overwritten by children
    frametype='Unknown'

    def __init__(self, spectrograph, files, det=1, par=None, binning=None):

        # Assign the internal list of files
        self._set_files(files)

        # Set the spectrograph
        self.spectrograph = load_spectrograph(spectrograph)

        # Assign the parameters to use to process the images
        if par is not None and not isinstance(par, pypeitpar.ProcessImagesPar):
            raise TypeError('Provided ParSet for processing images must be type ProcessImagesPar.')

        # TODO: This can't be called self.par because it may overwrite
        # the self.par of the derived classes (e.g. BiasFrame).  There may
        # be a better way to do this, but I'm punting for now.
        self.proc_par = pypeitpar.ProcessImagesPar() if par is None else par

        # Main (possible) outputs
        self.stack = None
        self.steps = []

        # Attributes set by load_images
        self.det = det
        self.raw_images = []
        self.headers = []
        self.datasec = []
        self.oscansec = []
        self.binning = binning      # Can be None

        self.proc_images = None  # Will be an ndarray

        # WARNING: Exposure time None by default here in the base class.
        # The exposure time is currently only defined by ScienceImage
        # and only used by build_rawvarframe
        # TODO: Is this only set by children?
        self.exptime = None

        # Constructed by process:
        self.crmask = None          # build_crmask
        self.rawvarframe = None     # build_rawvarframe
        self.rn2img = None          # build_rn2img
        self.bpm = None             # passed as an argument to process(), flat_field()
        self.pixel_flat = None      # passed as an argument to process(), flat_field()
        self.illum_flat = None        # passed as an argument to process(), flat_field()

    def _set_files(self, files, check=True):
        """
        Assign the provided files to :attr:`files`.

        Args:
            files (None, :obj:`str`, :obj:`list`):
                The files to process.
            check (:obj:`bool`, optional):
                Check that the files exist on disk.

        Raises:
            PypeItError:
                Raised if the input objects have the wrong type.
        """
        if files is None:
            self.files = []
        elif isinstance(files, str):
            self.files = [files]
        elif isinstance(files, list):
            if not np.all([isinstance(f, str) for f in files]):
                msgs.error('File list elements must be strings.')
            self.files = files
        else:
            msgs.error('Provides files must be None, a string name, or a list of strings.')

        if check:
            self._check_files()

    def _check_files(self):
        """
        Check that files in :attr:`files` exist.

        Raises:
            PypeItError:
                Raised if any of the files don't exist.
        """
        for f in self.files:
            if not os.path.isfile(f):
                msgs.error('{0} does not exist!'.format(f))

    # TODO: This is currently only use by BiasFrame as a test.  Now that
    # ProcessImages takes in these other parameter sets, we'll need to
    # be more clever as to how to do this, or create methods specific to
    # each child class.
#    @classmethod
#    def from_fits(cls, fits_file, **kwargs):
#        """
#        Instantiate from a FITS file
#
#        Parameters
#        ----------
#        fits_file : str
#        kwargs : passed to the __init__
#
#        Returns
#        -------
#        slf
#
#        """
#        if not os.path.isfile(fits_file):
#            msgs.error("FITS file not found: {:s}".format(fits_file))
#        # Load
#        hdul = fits.open(fits_file)
#        head0 = hdul[0].header
#        file_list = []
#        for key in head0:
#            if 'FRAME' in key:
#                file_list.append(head0[key])
#
#        # Initialize
#        slf = cls(head0['INSTRUME'], file_list=file_list,
#                  overscan_par=OverscanPar.from_header(head0),
#                  combine_par=CombineFramesPar.from_header(head0),
#                  lacosmic_par=LACosmicPar.from_header(head0), **kwargs)
#
#        # Fill
#        slf.stack = hdul[0].data
#        return slf

    @property
    def nfiles(self):
        """
        The number of files to process.
        """
        return len(self.files)

    @property
    def nloaded(self):
        """
        The number of raw images loaded, ready for use.
        """
        return len(self.raw_images)

    def load_images(self, files, det=None, binning=None):
        """
        Load image header, data, and relevant image sections into
        memory.

        Args:
            files (:obj:`str`, :obj:`list`):
                One or more files to read and process.
            det (:obj:`int`, optional):
                The 1-indexed detector to read.  If None, :attr:`det` is
                used.
            binning (:obj:`str`, :obj:`list`, optional):
                Binning of the images in PypeIt format (a
                comma-separated string ordered by spatial then spectral
                binning in numbers of pixels).  If None, this is parsed
                from the file headers.

        Returns:
            Five lists are returned::
                - numpy arrays with the raw image data.  See
                  :func:`pypeit.spectrographs.spectrograph.Spectrograph.load_raw_frame`.
                - :class:`astropy.io.fits.Header` instances with the
                  relevant header for the image data.  See
                  :func:`pypeit.spectrographs.spectrograph.Spectrograph.load_raw_frame`.
                - :obj:`str` objects with the PypeIt-format binning
                - :obj:`slice` objects that select the data sections of
                  the returned image data, accounting for any image binning.
                - :obj:`slice` objects that select the overscan sections
                  of the returned image data, accounting for any image binning.

        """
        # TODO: I'd like to allow the method to use the already assigned
        # internal files in the case that files is None.
        self._set_files(files)

        # Set the detector
        if det is not None:
            self.det = det

        # Zero out any previous load
        # TODO: Do we need to be more explicit than this?  I.e., use del
        self.raw_images = [None]*self.nfiles
        self.headers = [None]*self.nfiles
        self.binning = [None]*self.nfiles if binning is None else binning
        self.datasec = [None]*self.nfiles
        self.oscansec = [None]*self.nfiles

        for i in range(self.nfiles):
            # Load the image data and headers
            self.raw_images[i], self.headers[i] \
                    = self.spectrograph.load_raw_frame(self.files[i], det=self.det)

            if self.binning[i] is None:
                self.binning[i] = self.spectrograph.parse_binning(self.headers[i])

            # Get the data sections, one section per amplifier
            datasec, one_indexed, include_end, transpose \
                    = self.spectrograph.get_image_section(inp=self.headers[i], det=self.det,
                                                          section='datasec')
            self.datasec[i] = [ parse.sec2slice(sec, one_indexed=one_indexed,
                                                include_end=include_end, require_dim=2,
                                                transpose=transpose, binning=self.binning[i])
                                    for sec in datasec ]
            # Get the overscan sections, one section per amplifier
            oscansec, one_indexed, include_end, transpose \
                    = self.spectrograph.get_image_section(inp=self.headers[i], det=self.det,
                                                          section='oscansec')
            self.oscansec[i] = [ parse.sec2slice(sec, one_indexed=one_indexed,
                                                 include_end=include_end, require_dim=2,
                                                 transpose=transpose, binning=self.binning[i])
                                    for sec in oscansec ]
        # Include step
        self.steps.append(inspect.stack()[0][3])

        # Return
        return self.raw_images, self.headers, self.datasec, self.oscansec

    def apply_gain(self, stack, trim=True):
        """
        Apply gain (instead of ampsec scale)

        Parameters
        ----------

        Returns
        -------
        self.mspixelflat -- Modified internally

        """
        # TODO: This is overkill when self.datasec is loaded, and this
        # call is made for a few of the steps.  Can we be more
        # efficient?
        datasec_img = self.spectrograph.get_datasec_img(self.file_list[0], det=self.det)
        if trim:
            datasec_img = procimg.trim_frame(datasec_img, datasec_img < 1)
        if stack.shape != datasec_img.shape:
            raise ValueError('Shape mismatch: {0} {1}'.format(stack.shape, datasec_img.shape))
        
        gain = self.spectrograph.detector[self.det-1]['gain']
        if self.spectrograph.detector[self.det-1]['numamplifiers'] == 1 \
                and not isinstance(gain, list):
            gain = [gain]
        stack *= procimg.gain_frame(datasec_img,self.spectrograph.detector[self.det-1]['numamplifiers'],gain)
        # Step
        self.steps.append(inspect.stack()[0][3])

        # Return
        return stack

    def bias_subtract(self, raw_images, msbias, trim=True, force=False, par=None):
        """
        Subtract the bias.

        Parameters
        ----------
        msbias : ndarray, str (optional)
          If ndarray, the input is a Bias image
          If str, the input is guides the Bias subtraction method e.g.  'overscan'
        trim

        Returns
        -------

        """
        proc_images = None
        # Check if the bias has already been subtracted
        if (inspect.stack()[0][3] in self.steps) & (not force):
            msgs.warn("Images already bias subtracted.  Use force=True to reset proc_images "
                      "and do it again. Returning...")
            return

        # Set the parameters
        if par is not None and not isinstance(par, pypeitpar.ProcessImagesPar):
            raise TypeError('Provided ParSet for must be type ProcessImagesPar.')
        if par is not None:
            self.proc_par = par

        # If trimming, get the image identifying amplifier used for the
        # data section
        datasec_img = self.spectrograph.get_datasec_img(self.file_list[0], det=self.det)

        msgs.info("Bias subtracting your image(s)")
        # Reset proc_images -- Is there any reason we wouldn't??
        numamplifiers = self.spectrograph.detector[self.det-1]['numamplifiers']
        for kk,image in enumerate(raw_images):
            # Bias subtract (move here from procimg)
            if isinstance(msbias, np.ndarray):
                msgs.info("Subtracting bias image from raw frame")
                # Trim?
                if trim:
                    image = procimg.trim_frame(image, datasec_img < 1)
                temp = image-msbias
            elif isinstance(msbias, str) and msbias == 'overscan':
                msgs.info("Using overscan to subtact")
                temp = procimg.subtract_overscan(image, numamplifiers, self.datasec, self.oscansec,
                                                 method=self.proc_par['overscan'],
                                                 params=self.proc_par['overscan_par'])
                # Trim?
                if trim:
                    temp = procimg.trim_frame(temp, datasec_img < 1)
            else:
                msgs.error('Could not subtract bias level with the input bias approach.')

            # Save
            if kk==0:
                # Instantiate proc_images
                proc_images = np.zeros((temp.shape[0], temp.shape[1], self.nloaded))
            proc_images[:,:,kk] = temp.copy()

        # Step
        self.steps.append(inspect.stack()[0][3])
        return proc_images

    def combine(self, proc_images, par=None):
        """
        Combine the processed images

        Returns
        -------
        self.stack : ndarray

        """
        # Set the parameters
        if par is not None and not isinstance(par, pypeitpar.ProcessImagesPar):
            raise TypeError('Provided ParSet for must be type ProcessImagesPar.')
        if par is not None:
            self.proc_par = par

        # Now we can combine
        saturation = self.spectrograph.detector[self.det-1]['saturation']
        stack = combine.comb_frames(proc_images, frametype=self.frametype,saturation=saturation,
                                    method=self.proc_par['combine'],
                                    satpix=self.proc_par['satpix'],
                                    cosmics=self.proc_par['sigrej'],
                                    n_lohi=self.proc_par['n_lohi'],
                                    sig_lohi=self.proc_par['sig_lohi'],
                                    replace=self.proc_par['replace'])
        # Step
        self.steps.append(inspect.stack()[0][3])
        return stack

    ## JFH ToDO Scienceimage is the only class currently using this method, and it is not used in this method.
    # Since I prefer not to make a ScienceImage a child of processimages (since it does not make sense with
    # Science image working on lists of images) I'm moving this method there.
#    def build_crmask(self, stack, varframe=None, par=None, binning=None):
#        """
#        Generate the CR mask frame
#
#        Wrapper to procimg.lacosmic
#
#        Parameters
#        ----------
#        varframe : ndarray, optional
#
#        Returns
#        -------
#        self.crmask : ndarray
#          1. = Masked CR
#
#        """
#        # Set the parameters
#        if par is not None and not isinstance(par, pypeitpar.ProcessImagesPar):
#            raise TypeError('Provided ParSet for must be type ProcessImagesPar.')
#        if par is not None:
#            self.proc_par = par
#
#        # Run LA Cosmic to get the cosmic ray mask
#        saturation = self.spectrograph.detector[self.det-1]['saturation']
#        nonlinear = self.spectrograph.detector[self.det-1]['nonlinear']
#        sigclip, objlim = self.spectrograph.get_lacosmics_par(self.proc_par,binning=binning)
#        self.crmask = procimg.lacosmic(self.det, stack, saturation, nonlinear,
#                                         varframe=varframe, maxiter=self.proc_par['lamaxiter'],
#                                         grow=self.proc_par['grow'],
#                                         remove_compact_obj=self.proc_par['rmcompact'],
#                                         sigclip=sigclip,
#                                         sigfrac=self.proc_par['sigfrac'],
#                                         objlim=objlim)
#
#        # Step
#        self.steps.append(inspect.stack()[0][3])
#        # Return
#        return self.crmask

    def flat_field(self, stack, pixel_flat, bpm, illum_flat=None):
        """
        Flat field the stack image

        pixel_flat and illum_flat are passed here to force users to
        consider that they're needed when calling flat_field().

        Wrapper to arflat.flatfield()

        Returns
        -------
        self.stack : ndarray
          Flat fielded

        """
        # Assign the relevant data to self
        self.pixel_flat = pixel_flat
        self.bpm = bpm
        self.illum_flat = illum_flat

        # Check that the bad-pixel mask is available
        if self.bpm is None:
            msgs.error('No bpm for {0}'.format(self.spectrograph.spectrograph))

        msgs.info("Flat fielding your image")
        # Flat-field the data and return the result

        stack = flat.flatfield(stack, self.pixel_flat, self.bpm, illum_flat=self.illum_flat)
        return stack

    def process(self, bias_subtract=None, apply_gain=False, trim=True, overwrite=False,
                pixel_flat=None, bpm=None, illum_flat=None):
        """
        Process the images from loading to combining

        Parameters
        ----------
        bias_subtract : str or ndarray or None
          Guides bias subtraction
        apply_gain : bool, optional
          Apply gain to the various amplifier regions
        trim : bool, optional
        overwrite :
        pixel_flat : ndarray or None
          This is the normalized pixel flat (i.e. no blaze, no slit illumination profile).
          The values of this array should have a scatter about 1.0

        Returns
        -------
        self.stack : ndarray

        """

        # Over-write?
        # TODO: This should probably raise an error.
        if (inspect.stack()[0][3] in self.steps) & (not overwrite):
            msgs.warn("Images already combined.  Use overwrite=True to do it again.")
            return

        # JFH The fact that all these codes have no arguments and no
        # return values make the control flow very hard to follow.  I
        # realize that everything has global scope in a class, but
        # inputs and outputs to functions make code flow understandable.

        # Load images
        if 'load_images' not in self.steps:
            self.raw_images, self.headers, self.datasec, self.oscansec \
                    = self.load_images(self.file_list)

        # Bias subtract
        if bias_subtract is not None:
            self.proc_images = self.bias_subtract(self.raw_images, bias_subtract, trim=trim)
        elif 'bias_subtract' not in self.steps:
            msgs.warn("Your images have not been bias subtracted!")

        # Create proc_images from raw_images if need be
        #   Mainly if no bias subtraction was performed
        if self.proc_images is None:
            # Trim even if not bias subtracting
            temp = self.raw_images[0]
            if trim:
                datasec_img = self.spectrograph.get_datasec_img(self.file_list[0], det=self.det)
                temp = procimg.trim_frame(temp, datasec_img < 1)
            self.proc_images = np.zeros((temp.shape[0], temp.shape[1], self.nloaded))
            for kk,image in enumerate(self.raw_images):
                self.proc_images[:,:,kk] = procimg.trim_frame(image, datasec_img < 1) \
                                                if trim else image

        # Combine
        self.stack = self.proc_images[:,:,0] if self.proc_images.shape[2] == 1 else self.combine(self.proc_images)
        self.raw_stack = self.stack

        # Apply gain?
        if apply_gain:
            self.stack = self.apply_gain(self.stack, trim=trim)

        # Flat field?
        if pixel_flat is not None:
            self.stack = self.flat_field(self.stack, pixel_flat, bpm, illum_flat=illum_flat)

        # Done
        return self.stack.copy()

    def build_rn2img(self, trim=True):
        """
        Generate the model read noise squared image

        Currently only used by ScienceImage.

        Wrapper to procimg.rn_frame

        Returns
        -------
        self.rn2img : ndarray

        """
        msgs.info("Generating read noise image from detector properties and amplifier layout)")
        datasec_img = self.spectrograph.get_datasec_img(self.file_list[0], det=self.det)
        if trim:
            datasec_img = procimg.trim_frame(datasec_img, datasec_img < 1)
        detector = self.spectrograph.detector[self.det-1]
        self.rn2img = procimg.rn_frame(datasec_img, detector['gain'], detector['ronoise'], numamplifiers=detector['numamplifiers'])

        self.steps.append(inspect.stack()[0][3])
        # Return
        return self.rn2img

    def build_rawvarframe(self, trim=True):
        """
        Generate the Raw Variance frame

        Currently only used by ScienceImage.

        Wrapper to procimg.variance_frame

        Returns
        -------
        self.rawvarframe : ndarray

        """
        msgs.info("Generating raw variance frame (from detected counts [flat fielded])")
        datasec_img = self.spectrograph.get_datasec_img(self.file_list[0], det=self.det)
        if trim:
            datasec_img = procimg.trim_frame(datasec_img, datasec_img < 1)
        detector = self.spectrograph.detector[self.det-1]
        self.rawvarframe = procimg.variance_frame(datasec_img, self.stack,
                                                    detector['gain'], detector['ronoise'],
                                                    numamplifiers=detector['numamplifiers'],
                                                    darkcurr=detector['darkcurr'],
                                                    exptime=self.exptime)

        # Step
        self.steps.append(inspect.stack()[0][3])
        # Return
        return self.rawvarframe


    def show(self, attr='stack', idx=None, display='ginga'):
        """
        Show an image

        Parameters
        ----------
        attr : str, optional
          Internal name of the image to show
            proc_image, raw_image, stack
        idx : int, optional
          Specifies the index of the raw or processed image
          Required if proc_image or raw_image is called
        display : str

        Returns
        -------

        """
        if 'proc_image' in attr:
            img = self.proc_images[:,:,idx]
        elif 'raw_image' in attr:
            img = self.raw_images[idx]
        elif 'stack' in attr:
            img = self.stack
        else:
            msgs.warn("Options:  proc_image, raw_image, stack")
            return
        # Show
        viewer, ch = ginga.show_image(img)

    def write_stack_to_fits(self, outfile, overwrite=True):
        """
        Write the combined image to disk as a FITS file

        Parameters
        ----------
        outfile : str
        overwrite

        Returns
        -------

        """
        if self.stack is None:
            msgs.warn("You need to generate the stack before you can write it!")
            return
        #
        hdu = fits.PrimaryHDU(self.stack)
        # Add raw_files to header
        for i in range(self.nfiles):
            hdrname = "FRAME{0:03d}".format(i+1)
            hdu.header[hdrname] = self.file_list[i]
        # Spectrograph
        hdu.header['INSTRUME'] = self.spectrograph.spectrograph
        # Parameters
        self.proc_par.to_header(hdu.header)
        # Steps
        steps = ','
        hdu.header['STEPS'] = steps.join(self.steps)
        # Finish
        hlist = [hdu]
        hdulist = fits.HDUList(hlist)
        hdulist.writeto(outfile, overwrite=overwrite)
        msgs.info("Wrote stacked image to {:s}".format(outfile))

    def __repr__(self):
        txt = '<{:s}: nimg={:d}'.format(self.__class__.__name__,
                                         self.nfiles)
        if len(self.steps) > 0:
            txt+= ' steps: ['
            for step in self.steps:
                txt += '{:s}, '.format(step)
            txt = txt[:-2]+']'  # Trim the trailing comma
        txt += '>'
        return txt


# TODO Add a function here that just reads in a fits file given a filename. Guess the instrument from the headers.
