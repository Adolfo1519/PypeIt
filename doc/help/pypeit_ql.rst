.. code-block:: console

    $ pypeit_ql -h
    usage: pypeit_ql [-h] [--raw_files RAW_FILES [RAW_FILES ...]]
                     [--raw_path RAW_PATH] [--ext EXT]
                     [--sci_files SCI_FILES [SCI_FILES ...]]
                     [--redux_path REDUX_PATH] [--parent_calib_dir PARENT_CALIB_DIR]
                     [--setup_calib_dir SETUP_CALIB_DIR] [--clean] [--calibs_only]
                     [--overwrite_calibs] [--slitspatnum SLITSPATNUM]
                     [--maskID MASKID] [--boxcar_radius BOXCAR_RADIUS]
                     [--det DET [DET ...]] [--no_stack] [--ignore_std]
                     [--snr_thresh SNR_THRESH] [--coadd]
                     spectrograph
    
    Script to produce quick-look PypeIt reductions
    
    positional arguments:
      spectrograph          A valid spectrograph identifier: bok_bc,
                            gemini_flamingos1, gemini_flamingos2,
                            gemini_gmos_north_e2v, gemini_gmos_north_ham,
                            gemini_gmos_north_ham_ns, gemini_gmos_south_ham,
                            gemini_gnirs, gtc_maat, gtc_osiris, gtc_osiris_plus,
                            jwst_nircam, jwst_nirspec, keck_deimos, keck_hires,
                            keck_kcwi, keck_lris_blue, keck_lris_blue_orig,
                            keck_lris_red, keck_lris_red_mark4, keck_lris_red_orig,
                            keck_mosfire, keck_nires, keck_nirspec_low, lbt_luci1,
                            lbt_luci2, lbt_mods1b, lbt_mods1r, lbt_mods2b,
                            lbt_mods2r, ldt_deveny, magellan_fire,
                            magellan_fire_long, magellan_mage, mdm_osmos_mdm4k,
                            mmt_binospec, mmt_bluechannel, mmt_mmirs, not_alfosc,
                            not_alfosc_vert, ntt_efosc2, p200_dbsp_blue,
                            p200_dbsp_red, p200_tspec, shane_kast_blue,
                            shane_kast_red, shane_kast_red_ret, soar_goodman_blue,
                            soar_goodman_red, tng_dolores, vlt_fors2, vlt_sinfoni,
                            vlt_xshooter_nir, vlt_xshooter_uvb, vlt_xshooter_vis,
                            wht_isis_blue, wht_isis_red
    
    optional arguments:
      -h, --help            show this help message and exit
      --raw_files RAW_FILES [RAW_FILES ...]
                            Either a PypeIt-formatted input file with the list of
                            raw images to process and the relevant path, or a space-
                            separated list of the filenames (e.g., "img1.fits
                            img2.fits"). For the latter entry mode, the path
                            containing the files is set using --raw_path. (default:
                            None)
      --raw_path RAW_PATH   Directory with the raw files to process. Ignored if a
                            PypeIt-formatted file is provided using the --rawfiles
                            option. (default: current working directory)
      --ext EXT             If raw file names are not provided directly using the
                            --rawfiles option, this sets the extension used when
                            searching for any files in the path defined by
                            --raw_path. All files found in the raw path with this
                            extension will be processed. (default: .fits)
      --sci_files SCI_FILES [SCI_FILES ...]
                            A space-separated list of raw file names that are
                            science exposures. These files must *also* be in the
                            list of raw files. Use of this option overrides the
                            automated PypeIt frame typing. (default: None)
      --redux_path REDUX_PATH
                            Path for the QL reduction outputs. (default: current
                            working directory)
      --parent_calib_dir PARENT_CALIB_DIR
                            Directory with/for calibrations for *all* instrument
                            configurations/setups. If provided, the data for your
                            instrument configuration will be placed or pulled from a
                            relevant sub-directory. If None, the redux_path is used.
                            (default: None)
      --setup_calib_dir SETUP_CALIB_DIR
                            Directory with/for calibrations specific to your
                            instrument configuration/setup. Use of this option
                            circumvents the automated naming system for the
                            configuration/setup sub-directories. If None, it is
                            assumed that no calibrations exist and they must be
                            created using the provided raw files. The top-level
                            directory is given by parent_calib_dir (or redux_path)
                            and the sub-directories follow the normal PypeIt naming
                            scheme. (default: None)
      --clean               Remove the existing output directories to force a fresh
                            reduction. If False, any existing directory structure
                            will remain, but any existing science files will still
                            be overwritten. (default: False)
      --calibs_only         Reduce only the calibrations? (default: False)
      --overwrite_calibs    Overwrite any existing calibration files? (default:
                            False)
      --slitspatnum SLITSPATNUM
                            Reduce the slit(s) as specified by the slitspatnum
                            value(s) (default: None)
      --maskID MASKID       Reduce the slit(s) as specified by the maskID value(s)
                            (default: None)
      --boxcar_radius BOXCAR_RADIUS
                            Set the radius for the boxcar extraction in arcseconds
                            (default: None)
      --det DET [DET ...]   A space-separated set of detectors or detector mosaics
                            to reduce. By default, *all* detectors or default
                            mosaics for this instrument will be reduced. Detectors
                            in a mosaic must be a mosaic "allowed" by PypeIt and
                            should be provided as comma-separated integers (with no
                            spaces). For example, to separately reduce detectors 1
                            and 5 for Keck/DEIMOS, you would use --det 1 5; to
                            reduce mosaics made up of detectors 1,5 and 3,7, you
                            would use --det 1,5 3,7 (default: None)
      --no_stack            Do *not* stack multiple science frames (default: True)
      --ignore_std          If standard star observations are automatically
                            detected, ignore those frames. Otherwise, they are
                            included with the reduction of the science frames.
                            (default: False)
      --snr_thresh SNR_THRESH
                            Change the default S/N threshold used during source
                            detection (default: None)
      --coadd               Perform default 2D coadding. (default: False)
    