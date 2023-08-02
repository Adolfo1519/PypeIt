""" Generate the wavelength templates for Keck/LRIS"""
import os

from pypeit.core.wavecal import templates


# Keck/DEIMOS

def keck_lris_red_mark4_R400(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_mark4_R400.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'Mark4', 'R400')

    basefiles = ['MasterWaveCalib_A_1_01_long.fits', 
                 'MasterWaveCalib_A_1_01_sunil.fits'] 
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0,1]
    slits = [2048, 2045]
    wv_cuts = [9320.]
    assert len(wv_cuts) == len(slits)-1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)

def keck_lris_red_orig_R150_7500(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R150_7500_ArHgNe.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R150_7500_orig',)

    basefiles = ['WaveCalib_A_0_DET01_S0662.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0]
    slits = [662]
    wv_cuts = []
    assert len(wv_cuts) == len(slits)-1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)


def keck_lris_red_orig_R300_5000(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R300_5000_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R300_5000_orig',)

    basefiles = ['WaveCalib_A_0_DET01_S1456.fits', 'WaveCalib_A_0_DET01_S0783.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0,1]
    slits = [1456, 783]
    wv_cuts = [5377.]
    assert len(wv_cuts) == len(slits)-1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)

def keck_lris_red_orig_R400_8500(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R400_8500_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R400_8500_orig',)

    basefiles = ['WaveCalib_A_0_DET01_S0180.fits', 'WaveCalib_A_0_DET01_S0131.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0,1]
    slits = [180,131]
    wv_cuts = [7330.]
    assert len(wv_cuts) == len(slits)-1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)


def keck_lris_red_orig_R600_5000(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R600_5000_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R600_5000_orig', )

    basefiles = ['WaveCalib_A_0_DET01_S0038.fits', 'WaveCalib_A_0_DET01_S0258.fits', 'WaveCalib_A_0_DET01_S0596.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0, 1, 2]
    slits = [38, 258, 596]
    wv_cuts = [6450., 6825.]
    assert len(wv_cuts) == len(slits) - 1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)


def keck_lris_red_orig_R600_7500(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R600_7500_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R600_7500_orig', )

    basefiles = ['WaveCalib_A_0_DET01_S1179.fits', 'WaveCalib_A_0_DET01_S0476.fits',
                 'WaveCalib_A_0_DET01_S0741.fits', 'WaveCalib_A_0_DET01_S1872.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0, 1, 2,3]
    slits = [1179, 476, 741, 1872]
    wv_cuts = [5250., 7585., 9480.]
    assert len(wv_cuts) == len(slits) - 1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)


def keck_lris_red_orig_R600_10000(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R600_10000_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R600_10000_orig', )

    basefiles = ['WaveCalib_A_0_DET01_S1567.fits', 'WaveCalib_A_0_DET01_S0543.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0, 1]
    slits = [1567, 543]
    wv_cuts = [9030.]
    assert len(wv_cuts) == len(slits) - 1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)


def keck_lris_red_orig_R831_8200(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R831_8200_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R831_8200_orig', )

    basefiles = ['WaveCalib_A_0_DET01_S0216.fits', 'WaveCalib_A_0_DET01_S1025.fits', 'WaveCalib_A_0_DET01_S1783.fits',
                 'WaveCalib_A_0_DET01_S0757.fits', 'WaveCalib_A_0_DET01_S1332.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0, 1, 2, 3, 4]
    slits = [216, 1025, 1783, 757, 1332]
    wv_cuts = [6060., 6290., 7100., 8330.]
    assert len(wv_cuts) == len(slits) - 1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)


def keck_lris_red_orig_R900_5500(overwrite=False):
    binspec = 1
    outroot = 'keck_lris_red_orig_R900_5500_ArCdHgNeZn.fits'
    # PypeIt fits
    wpath = os.path.join(templates.template_path, 'Keck_LRIS', 'R900_5500_orig', )

    basefiles = ['WaveCalib_A_0_DET01_S1966.fits', 'WaveCalib_A_0_DET01_S1864.fits', 'WaveCalib_A_0_DET01_S0590.fits']
    wfiles = [os.path.join(wpath, basefile) for basefile in basefiles]
    # Snippets
    ifiles = [0, 1, 2]
    slits = [1966, 1864, 590]
    wv_cuts = [6195., 6630.]
    assert len(wv_cuts) == len(slits) - 1
    # det_dict
    det_cut = None
    #
    templates.build_template(wfiles, slits, wv_cuts, binspec, outroot,
                             ifiles=ifiles, det_cut=det_cut, chk=True,
                             normalize=True, lowredux=False,
                             subtract_conti=True, overwrite=overwrite,
                             shift_wave=True)

# Run em
if __name__ == '__main__':
    # keck_lris_red_mark4_R400()#overwrite=True)
    # keck_lris_red_orig_R300_5000(overwrite=False)
    # keck_lris_red_orig_R150_7500(overwrite=False)
    # keck_lris_red_orig_R400_8500(overwrite=False)
    # keck_lris_red_orig_R600_5000(overwrite=False)
    # keck_lris_red_orig_R600_7500(overwrite=False)
    # keck_lris_red_orig_R600_10000(overwrite=False)
    # keck_lris_red_orig_R831_8200(overwrite=False)
    keck_lris_red_orig_R900_5500(overwrite=False)