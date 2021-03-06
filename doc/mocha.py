'''

generate plots for the mock challenge paper 


'''
import os 
import h5py 
import numpy as np 
import corner as DFM 
import scipy.optimize as op
from scipy.stats import norm as Norm
# --- gqp_mc ---
from gqp_mc import util as UT 
from gqp_mc import data as Data 
from gqp_mc import fitters as Fitters
# --- astro ---
from astropy.io import fits
from astroML.datasets import fetch_sdss_specgals
# --- plotting --- 
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as patches
if os.environ.get('NERSC_HOST') is None: 
    mpl.rcParams['text.usetex'] = True
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['axes.linewidth'] = 1.5
mpl.rcParams['axes.xmargin'] = 1
mpl.rcParams['xtick.labelsize'] = 'x-large'
mpl.rcParams['xtick.major.size'] = 5
mpl.rcParams['xtick.major.width'] = 1.5
mpl.rcParams['ytick.labelsize'] = 'x-large'
mpl.rcParams['ytick.major.size'] = 5
mpl.rcParams['ytick.major.width'] = 1.5
mpl.rcParams['legend.frameon'] = False


dir_mm = os.path.join(UT.dat_dir(), 'mini_mocha') 
dir_fig = os.path.join(UT.dat_dir(), 'mini_mocha') 

dir_doc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper', 'figs') 
dir_fbgs = os.path.join(os.path.dirname(os.path.dirname(UT.dat_dir())), 'feasiBGS') 


def BGS(): 
    ''' plot highlighting BGS footprint and redshift number density
    '''
    # read BGS MXXL galaxies 
    mxxl    = h5py.File(os.path.join(dir_fbgs, 'BGS_r20.0.hdf5'), 'r') 
    bgs     = mxxl['Data']
    ra_bgs  = bgs['ra'][...][::10]
    dec_bgs = bgs['dec'][...][::10]
    z_bgs   = np.array(bgs['z_obs'])
    
    # read SDSS galaxies from astroML (https://www.astroml.org/modules/generated/astroML.datasets.fetch_sdss_specgals.html)
    sdss        = fetch_sdss_specgals()
    ra_sdss     = sdss['ra'] 
    dec_sdss    = sdss['dec'] 
    
    # read GAMA objects
    f_gama = os.path.join(dir_fbgs, 'gama', 'dr3', 'SpecObj.fits') 
    gama = fits.open(f_gama)[1].data 

    fig = plt.figure(figsize=(15,5))
    
    gs1 = mpl.gridspec.GridSpec(1,1, figure=fig) 
    gs1.update(left=0.02, right=0.7)
    sub = plt.subplot(gs1[0], projection='mollweide')
    sub.grid(True, linewidth=0.1) 
    # DESI footprint 
    sub.scatter((ra_bgs - 180.) * np.pi/180., dec_bgs * np.pi/180., s=1, lw=0, c='k')
    # SDSS footprint 
    sub.scatter((ra_sdss - 180.) * np.pi/180., dec_sdss * np.pi/180., s=1, lw=0, c='C0')#, alpha=0.01)
    # GAMA footprint for comparison 
    gama_ra_min = (np.array([30.2, 129., 174., 211.5, 339.]) - 180.) * np.pi/180.
    gama_ra_max = (np.array([38.8, 141., 186., 223.5, 351.]) - 180.) * np.pi/180. 
    gama_dec_min = np.array([-10.25, -2., -3., -2., -35.]) * np.pi/180.
    gama_dec_max = np.array([-3.72, 3., 2., 3., -30.]) * np.pi/180.
    for i_f, field in enumerate(['g02', 'g09', 'g12', 'g15', 'g23']): 
        rect = patches.Rectangle((gama_ra_min[i_f], gama_dec_min[i_f]), 
                gama_ra_max[i_f] - gama_ra_min[i_f], 
                gama_dec_max[i_f] - gama_dec_min[i_f], 
                facecolor='C1')
        sub.add_patch(rect)
    sub.set_xlabel('RA', fontsize=20, labelpad=10) 
    sub.set_xticklabels(['', '', '$90^o$', '', '', '$180^o$', '', '', '$270^o$'])#, fontsize=10)
    sub.set_ylabel('Dec', fontsize=20)

    gs2 = mpl.gridspec.GridSpec(1,1, figure=fig) 
    gs2.update(left=0.70, right=0.98)#, wspace=0.05)
    sub = plt.subplot(gs2[0])
    sub.hist(z_bgs, range=[0.0, 1.], color='k', bins=100) 
    sub.hist(sdss['z'], range=[0.0, 1.], color='C0', bins=100) 
    sub.hist(np.array(gama['Z']), range=[0.0, 1.], color='C1', bins=100) 
    sub.set_xlabel('Redshift', fontsize=20) 
    sub.set_xlim([0., 0.6])
    sub.set_ylabel('dN/dz', fontsize=20) 

    def _fmt(x, pos):
        a, b = '{:.2e}'.format(x).split('e')
        a = a.split('.')[0]
        b = int(b)
        if b == 0: 
            return r'${}$'.format(a)
        else: 
            return r'${}\times10^{{{}}}$'.format(a, b)

    sub.get_yaxis().set_major_formatter(ticker.FuncFormatter(_fmt))
    plts = []  
    for clr in ['k', 'C0', 'C1']: 
        _plt = sub.fill_between([0], [0], [0], color=clr, linewidth=0)
        plts.append(_plt) 
    sub.legend(plts, ['DESI', 'SDSS', 'GAMA'], loc='upper right', handletextpad=0.3, prop={'size': 20}) 
    sub.set_xticklabels([]) 

    ffig = os.path.join(dir_fig, 'bgs.png')
    fig.savefig(ffig, bbox_inches='tight')
    fig.savefig(UT.fig_tex(ffig, pdf=True), bbox_inches='tight') 
    return None 


def FM_photo():
    ''' plot illustrating the forward model for photometry 
    '''
    from speclite import filters as specFilter

    # read forward modeled Lgal photometry
    photo, meta = Data.Photometry(sim='lgal', noise='legacy', lib='bc03', sample='mini_mocha')
    flux_g = photo['flux'][:,0] * 1e-9 * 1e17 * UT.c_light() / 4750.**2 * (3631. * UT.jansky_cgs())
    flux_r = photo['flux'][:,1] * 1e-9 * 1e17 * UT.c_light() / 6350.**2 * (3631. * UT.jansky_cgs())
    flux_z = photo['flux'][:,2] * 1e-9 * 1e17 * UT.c_light() / 9250.**2 * (3631. * UT.jansky_cgs()) # convert to 10^-17 ergs/s/cm^2/Ang
    ivar_g = photo['ivar'][:,0] * (1e-9 * 1e17 * UT.c_light() / 4750.**2 * (3631. * UT.jansky_cgs()))**-2.
    ivar_r = photo['ivar'][:,1] * (1e-9 * 1e17 * UT.c_light() / 6350.**2 * (3631. * UT.jansky_cgs()))**-2.
    ivar_z = photo['ivar'][:,2] * (1e-9 * 1e17 * UT.c_light() / 9250.**2 * (3631. * UT.jansky_cgs()))**-2. # convert to 10^-17 ergs/s/cm^2/Ang

    # read noiseless Lgal spectroscopy 
    specs, _ = Data.Spectra(sim='lgal', noise='none', lib='bc03', sample='mini_mocha') 
    # read in photometric bandpass filters 
    filter_response = specFilter.load_filters(
            'decam2014-g', 'decam2014-r', 'decam2014-z',
            'wise2010-W1', 'wise2010-W2', 'wise2010-W3', 'wise2010-W4')
    wave_eff = [filter_response[i].effective_wavelength.value for i in range(len(filter_response))]

    fig = plt.figure(figsize=(14,4))
    gs1 = mpl.gridspec.GridSpec(1,1, figure=fig) 
    gs1.update(left=0.02, right=0.7)
    sub = plt.subplot(gs1[0])
    _plt_sed, = sub.plot(specs['wave'], specs['flux_unscaled'][0], c='k', lw=0.5, ls=':', 
            label='LGal Spectral Energy Distribution')
    _plt_photo = sub.errorbar(wave_eff[:3], [flux_g[0], flux_r[0], flux_z[0]], 
            yerr=[ivar_g[0]**-0.5, ivar_r[0]**-0.5, ivar_z[0]**-0.5], fmt='.C3', markersize=10,
            label='forward modeled DESI photometry') 
    _plt_filter, = sub.plot([0., 0.], [0., 0.], c='k', ls='--', label='Broadband Filter Response') 
    for i in range(3): # len(filter_response)): 
        sub.plot(filter_response[i].wavelength, filter_response[i].response, ls='--') 
        sub.text(filter_response[i].effective_wavelength.value, 0.9, ['g', 'r', 'z'][i], fontsize=20, color='C%i' % i)
    sub.set_xlabel('wavelength [$A$]', fontsize=20) 
    sub.set_xlim(3500, 1e4)
    sub.set_ylabel('flux [$10^{-17} erg/s/cm^2/A$]', fontsize=20) 
    sub.set_ylim(0., 6.) 
    sub.legend([_plt_sed, _plt_photo, _plt_filter], 
            ['LGal Spectral Energy Distribution', 'forward modeled DESI photometry', 'Broadband Filter Response'], 
            loc='upper right', handletextpad=0.2, fontsize=15) 
    
    # Legacy imaging target photometry DR8
    bgs_true = h5py.File(os.path.join(UT.dat_dir(), 'bgs.1400deg2.rlim21.0.hdf5'), 'r')
    bgs_gmag = 22.5 - 2.5 * np.log10(bgs_true['flux_g'][...])
    bgs_rmag = 22.5 - 2.5 * np.log10(bgs_true['flux_r'][...]) 
    bgs_zmag = 22.5 - 2.5 * np.log10(bgs_true['flux_z'][...])
    rlim = (bgs_rmag < 20.) 
    
    photo_g = 22.5 - 2.5 * np.log10(photo['flux'][:,0])
    photo_r = 22.5 - 2.5 * np.log10(photo['flux'][:,1])
    photo_z = 22.5 - 2.5 * np.log10(photo['flux'][:,2])
        
    gs2 = mpl.gridspec.GridSpec(1,1, figure=fig) 
    gs2.update(left=0.76, right=1.)
    sub = plt.subplot(gs2[0])
    DFM.hist2d(bgs_gmag[rlim] - bgs_rmag[rlim], bgs_rmag[rlim] - bgs_zmag[rlim], color='k', levels=[0.68, 0.95], 
            range=[[-1., 3.], [-1., 3.]], bins=40, smooth=0.5, 
            plot_datapoints=False, fill_contours=False, plot_density=False, linewidth=0.5, ax=sub)
    sub.fill_between([0],[0],[0], fc='none', ec='k', label='Legacy Surveys Imaging') 
    sub.scatter(photo_g - photo_r, photo_r - photo_z, c='C3', s=1)#, label='forward modeled DESI photometry') 
    sub.set_xlabel('$g-r$', fontsize=20) 
    sub.set_xlim(0., 2.) 
    sub.set_xticks([0., 1., 2.]) 
    sub.set_ylabel('$r-z$', fontsize=20) 
    sub.set_ylim(0., 1.5) 
    sub.set_yticks([0., 1.]) 
    sub.legend(loc='upper left', fontsize=15) 

    ffig = os.path.join(dir_fig, 'fm_photo.png')
    fig.savefig(ffig, bbox_inches='tight')
    fig.savefig(UT.fig_tex(ffig, pdf=True), bbox_inches='tight') 
    return None 


def FM_spec():
    ''' plot illustrating the forward model for spectroscopy 
    '''
    # read noiseless Lgal spectroscopy 
    spec_s, meta = Data.Spectra(sim='lgal', noise='none', lib='bc03', sample='mini_mocha') 
    spec_bgs, _ = Data.Spectra(sim='lgal', noise='bgs0', lib='bc03', sample='mini_mocha') 
    
    fig = plt.figure(figsize=(10,4))
    sub = fig.add_subplot(111) 

    wsort = np.argsort(spec_bgs['wave']) 
    _plt, = sub.plot(spec_bgs['wave'][wsort], spec_bgs['flux'][0,wsort], c='C0', lw=0.5) 
    
    _plt_lgal, = sub.plot(spec_s['wave'], spec_s['flux'][0,:], c='k', ls='-', lw=1) 
    _plt_lgal0, = sub.plot(spec_s['wave'], spec_s['flux_unscaled'][0,:], c='k', ls=':', lw=0.5) 
    
    leg = sub.legend([_plt_lgal0, _plt_lgal, _plt], 
            ['LGal Spectral Energy Distribution', 'fiber aperture SED', 'forward modeled BGS spectrum'],
            loc='upper right', handletextpad=0.3, fontsize=17) 
    sub.set_xlabel('wavelength [$A$]', fontsize=20) 
    sub.set_xlim(3500, 1e4)
    sub.set_ylabel('flux [$10^{-17} erg/s/cm^2/A$]', fontsize=20) 
    sub.set_ylim(0., 6.) 

    ffig = os.path.join(dir_fig, 'fm_spec.png')
    fig.savefig(ffig, bbox_inches='tight')
    fig.savefig(UT.fig_tex(ffig, pdf=True), bbox_inches='tight') 
    return None 


def speculator():
    '''plot the SFH and ZH bases of speculator 
    '''
    ispeculator = Fitters.iSpeculator()

    tage = np.linspace(0., 13.7, 50) 
    
    fig = plt.figure(figsize=(12,4))
    sub = fig.add_subplot(121)
    for i, basis in enumerate(ispeculator._sfh_basis): 
        sub.plot(tage, basis(tage), label=r'$s_{%i}^{\rm SFH}$' % (i+1)) 
    sub.set_xlim(0., 13.7) 
    sub.set_ylabel(r'star formation rate [$M_\odot/{\rm Gyr}$]', fontsize=20) 
    sub.set_ylim(0., 0.18) 
    sub.set_yticks([0.05, 0.1, 0.15]) 
    sub.legend(loc='upper right', fontsize=20, handletextpad=0.2) 

    sub = fig.add_subplot(122)
    for i, basis in enumerate(ispeculator._zh_basis): 
        sub.plot(tage, basis(tage), label=r'$s_{%i}^{\rm ZH}$' % (i+1)) 
    sub.set_xlim(0., 13.7) 
    sub.set_ylabel('metallicity $Z$', fontsize=20) 
    sub.set_ylim(0., None) 
    sub.legend(loc='upper left', fontsize=20, handletextpad=0.2) 

    bkgd = fig.add_subplot(111, frameon=False)
    bkgd.set_xlabel(r'$t_{\rm age}$ [Gyr]', labelpad=10, fontsize=25) 
    bkgd.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
    fig.subplots_adjust(wspace=0.2)
    _ffig = os.path.join(dir_doc, 'speculator.png') 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def mcmc_posterior(): 
    ''' plot that includes a corner plot and also demonstrates how the best-fit
    reproduces the data 
    '''
    igal = 0 
    ########################################################################
    # read meta data 
    ########################################################################
    photo, meta = Data.Photometry(sim='lgal', noise='legacy', lib='bc03', sample='mini_mocha') 
    ########################################################################
    # read MC chain 
    ########################################################################
    f_mcmc = os.path.join(dir_mm, 'ispeculator',
            'lgal.specphoto.noise_bgs0_legacy.emulator.%i.hdf5' % igal)
    mcmc = h5py.File(f_mcmc, 'r')

    ########################################################################
    # compile labels and truths
    ########################################################################
    lbls = [r'$\log M_*$', r'$\beta_1^{\rm SFH}$', r'$\beta_2^{\rm SFH}$',
            r'$\beta_3^{\rm SFH}$', r'$\beta_4^{\rm SFH}$', 
            r'$\gamma_1^{\rm ZH}$', r'$\gamma_2^{\rm ZH}$', 
            r'$\tau$', r'$f_{\rm fiber}$']
    truths = [None for _ in mcmc['theta_names'][...]]
    truths[0] = meta['logM_total'][igal]
    truths[8] = (photo['fiberflux_r_true'][igal]/photo['flux_r_true'][igal]) 

    ########################################################################
    # figure 
    ########################################################################
    fig = plt.figure(figsize=(12,17))
    gs1 = fig.add_gridspec(nrows=9, ncols=9, top=0.95, bottom=0.23) 
    #left=0.1, right=0.9)
    for i in range(9): 
        for j in range(9): 
            _ = fig.add_subplot(gs1[i,j])

    DFM.corner(mcmc['mcmc_chain'][...][:,:len(lbls)],
            range=mcmc['prior_range'][...][:len(lbls)],
            quantiles=[0.16, 0.5, 0.84], levels=[0.68, 0.95], nbin=40, smooth=True, 
            truths=truths, labels=lbls, label_kwargs={'fontsize': 15},
            labelpad=10, fig=fig) 

    gs2 = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[1,3], top=0.18, bottom=0.05)
    ax1 = fig.add_subplot(gs2[0,0]) 
    n_photo = len(mcmc['flux_photo_data'][...])
    ax1.errorbar(np.arange(n_photo), mcmc['flux_photo_data'][...], 
            yerr=mcmc['flux_photo_ivar_data'][...]**-0.5, fmt='.k', label='data')
    ax1.scatter(np.arange(n_photo), mcmc['flux_photo_model'][...], 
            c='C1', label=r'model($\theta_{\rm med}$)') 
    ax1.legend(loc='upper left', markerscale=3, handletextpad=0.2, fontsize=15) 
    ax1.set_xticks([0, 1, 2, 3, 4]) 
    ax1.set_xticklabels(['$g$', '$r$', '$z$', 'W1', 'W2']) 
    ax1.set_xlim(-0.5, n_photo-0.5)

    ax2 = fig.add_subplot(gs2[0,1]) 
    ax2.plot(mcmc['wavelength_data'][...], mcmc['flux_spec_data'][...], c='k',
            lw=1) 
    ax2.plot(mcmc['wavelength_model'][...], mcmc['flux_spec_model'][...], c='C1',
            ls='--', lw=1) 
    ax2.set_xlabel('wavelength [$\AA$]', fontsize=20) 
    ax2.set_xlim(3600., 9800.)
    
    _ffig = os.path.join(dir_doc, 'mcmc_posterior.png') 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    plt.close()
    return None 


def inferred_props(method='ifsps', model=None, sfr='100myr'):
    ''' compare inferred physical galaxy properties of each galaxy to its
    corresponding intrinsic values 
    '''
    if sfr == '100myr': dt = 0.1
    ngal = 97
    sims = ['lgal', 'tng'] 
    
    Mstar_inputs, logSFR_inputs = [], [] 
    Mstar_infs, logSFR_infs = [], [] 
    for sim in sims: 
        if sim != 'lgal': continue 
        # read noiseless Lgal spectra of the spectral_challenge mocks
        specs, meta = Data.Spectra(sim=sim, noise='bgs0', lib='bc03', sample='mini_mocha') 
        # read Lgal photometry of the mini_mocha mocks
        photo, _ = Data.Photometry(sim=sim, noise='legacy', lib='bc03', sample='mini_mocha')
        
        if method == 'ifsps': ifitter = Fitters.iFSPS()
        elif method == 'ispeculator': ifitter = Fitters.iSpeculator()

        igals, theta_inf = [], [] 
        for igal in range(ngal):  
            _fbf = Fbestfit_specphoto(igal, sim=sim, noise='bgs0_legacy',
                    method=method, model=model)
            if not os.path.isfile(_fbf): 
                print('     %s does not exist' % _fbf)
                continue 
            fbf = h5py.File(_fbf, 'r')  
            mcmc_chain = fbf['mcmc_chain'][...].copy() 
            fbf.close() 

            _theta_inf = np.percentile(mcmc_chain, [2.5, 16, 50, 84, 97.5], axis=0)

            igals.append(igal) 
            theta_inf.append(_theta_inf) 

        igals = np.array(igals)

        # input properties 
        Mstar_input = [meta['logM_total'][i] for i in igals] # total mass 
        logSFR_input= np.log10([meta['sfr_%s' % sfr][i] for i in igals])

        # inferred properties
        Mstar_inf   = np.array([_tt[:,0] for _tt in theta_inf])
        logSFR_inf  = np.array([_tt[:,-1] for _tt in theta_inf])

        Mstar_inputs.append(Mstar_input) 
        logSFR_inputs.append(logSFR_input) 
        
        Mstar_infs.append(Mstar_inf) 
        logSFR_infs.append(logSFR_inf) 
    
    fig = plt.figure(figsize=(12,8))
    for i in range(len(sims)):
        if sims[i] != 'lgal': continue 
        Mstar_input = Mstar_inputs[i] 
        Mstar_inf = Mstar_infs[i]
        logSFR_input = logSFR_inputs[i]
        logSFR_inf = logSFR_infs[i]

        # compare total stellar mass 
        sub = fig.add_subplot(2,3,2*i+1) 
        sub.errorbar(Mstar_input, Mstar_inf[:,2], 
                yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
        sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
        sub.text(0.05, 0.95, sims[i].upper(), ha='left', va='top', transform=sub.transAxes, fontsize=25)

        sub.set_xlim(9., 12.) 
        if i == 0: sub.set_xticklabels([])
        sub.set_ylim(9., 12.) 
        sub.set_yticks([9., 10., 11., 12.]) 
        if i == 0: sub.set_title(r'$\log M_*$', fontsize=25)

        # compare SFR 
        sub = fig.add_subplot(2,3,2*i+2) 
        sub.errorbar(logSFR_input, logSFR_inf[:,2], 
                yerr=[logSFR_inf[:,2]-logSFR_inf[:,1], logSFR_inf[:,3]-logSFR_inf[:,2]], fmt='.C0')
        sub.plot([-3., 2.], [-3., 2.], c='k', ls='--') 
        sub.set_xlim(-3., 2.) 
        if i == 0: sub.set_xticklabels([])
        sub.set_ylim(-3., 2.) 
        sub.set_yticks([-2., 0., 2.]) 
        if sfr == '1gyr': lbl_sfr = '1Gyr'
        elif sfr == '100myr': lbl_sfr = r'100{\rm Myr}'
        if i == 0: sub.set_title(r'$\log{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
        
        # compare Z 
        sub = fig.add_subplot(2,3,2*i+3) 
        if i == 0: sub.set_title(r'mass-weighted $Z$', fontsize=25)
        if i == 0: sub.set_xticklabels([])

    bkgd = fig.add_subplot(111, frameon=False)
    bkgd.set_xlabel(r'$\theta_{\rm true}$', fontsize=25) 
    bkgd.set_ylabel(r'$\widehat{\theta}$', labelpad=10, fontsize=25) 
    bkgd.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
    fig.subplots_adjust(wspace=0.225, hspace=0.1)
    _ffig = os.path.join(dir_doc, 'inferred_prop.%s.%s.sfr_%s.comparison.png' %
            (method, model, sfr)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def _speculator_fsps(sfr='100myr'):
    ''' compare inferred physical galaxy properties from speculator versus
    actually running fsps 

    notes
    -----
    * only Lgal implemented
    '''
    if sfr == '100myr': dt = 0.1
    ngal = 97
    
    Mstar_emul, logSFR_emul = [], [] 
    Mstar_fsps, logSFR_fsps = [], [] 

    igals = []
    for igal in range(ngal):  
        _femul = Fbestfit_specphoto(igal, sim='lgal', noise='bgs0_legacy',
                method='ispeculator', model='emulator')
        _ffsps = Fbestfit_specphoto(igal, sim='lgal', noise='bgs0_legacy',
                method='ispeculator', model='fsps')
        if not (os.path.isfile(_femul) and os.path.isfile(_ffsps)):
            print('     %s or' % _femul)
            print('     %s does not exist' % _ffsps)
            continue 
        igals.append(igal) 

        femul       = h5py.File(_femul, 'r')  
        mcmc_emul   = femul['mcmc_chain'][...].copy() 
        _theta_emul = np.percentile(mcmc_emul, [2.5, 16, 50, 84, 97.5], axis=0)
        femul.close() 
        
        ffsps       = h5py.File(_ffsps, 'r')  
        mcmc_fsps   = ffsps['mcmc_chain'][...].copy() 
        _theta_fsps = np.percentile(mcmc_fsps, [2.5, 16, 50, 84, 97.5], axis=0)
        ffsps.close() 
    
        Mstar_emul.append(_theta_emul[:,0])
        logSFR_emul.append(_theta_emul[:,-1])
        Mstar_fsps.append(_theta_fsps[:,0])
        logSFR_fsps.append(_theta_fsps[:,-1])

    igals = np.array(igals)
    Mstar_emul = np.array(Mstar_emul)
    logSFR_emul = np.array(logSFR_emul)
    Mstar_fsps = np.array(Mstar_fsps)
    logSFR_fsps = np.array(logSFR_fsps)
    
    fig = plt.figure(figsize=(8,4))
    # compare total stellar mass 
    sub = fig.add_subplot(121) 
    #sub.errorbar(Mstar_input, Mstar_inf[:,2], 
    #        yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
    sub.scatter(Mstar_fsps[:,2], Mstar_emul[:,2], c='C0') 
    sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
    sub.text(0.05, 0.95, 'L-Galaxies', ha='left', va='top', transform=sub.transAxes, fontsize=25)

    sub.set_xlim(9., 12.) 
    sub.set_ylim(9., 12.) 
    sub.set_yticks([9., 10., 11., 12.]) 
    sub.set_title(r'$\log M_*$', fontsize=25)

    # compare SFR 
    sub = fig.add_subplot(122) 
    #sub.errorbar(logSFR_input, logSFR_inf[:,2], 
    #        yerr=[logSFR_inf[:,2]-logSFR_inf[:,1], logSFR_inf[:,3]-logSFR_inf[:,2]], fmt='.C0')
    sub.scatter(logSFR_fsps[:,2], logSFR_emul[:,2], c='C0')
    sub.plot([-3., 2.], [-3., 2.], c='k', ls='--') 
    sub.set_xlim(-3., 2.) 
    sub.set_ylim(-3., 2.) 
    sub.set_yticks([-2., 0., 2.]) 
    if sfr == '1gyr': lbl_sfr = '1Gyr'
    elif sfr == '100myr': lbl_sfr = r'100{\rm Myr}'
    sub.set_title(r'$\log{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    
    bkgd = fig.add_subplot(111, frameon=False)
    bkgd.set_xlabel(r'$\theta_{\rm true}$', fontsize=25) 
    bkgd.set_ylabel(r'$\widehat{\theta}$', labelpad=10, fontsize=25) 
    bkgd.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
    fig.subplots_adjust(wspace=0.225, hspace=0.1)
    _ffig = os.path.join(dir_doc, '_speculator_fsps.prop_comparison.png') 
    fig.savefig(_ffig, bbox_inches='tight') 

    
    igal = np.random.choice(igals) 
    _femul = Fbestfit_specphoto(igal, sim='lgal', noise='bgs0_legacy',
            method='ispeculator', model='emulator')
    _ffsps = Fbestfit_specphoto(igal, sim='lgal', noise='bgs0_legacy',
            method='ispeculator', model='fsps')
    
    femul       = h5py.File(_femul, 'r')  
    mcmc_emul   = femul['mcmc_chain'][...].copy() 
    _theta_emul = np.percentile(mcmc_emul, [2.5, 16, 50, 84, 97.5], axis=0)
    femul.close() 
    
    ffsps       = h5py.File(_ffsps, 'r')  
    mcmc_fsps   = ffsps['mcmc_chain'][...].copy() 
    _theta_fsps = np.percentile(mcmc_fsps, [2.5, 16, 50, 84, 97.5], axis=0)
    ffsps.close() 
    
    fig = DFM.corner(mcmc_emul, quantiles=[0.16, 0.5, 0.84], levels=[0.68, 0.95], 
            color='C0', nbin=20, smooth=True) 
    DFM.corner(mcmc_fsps, quantiles=[0.16, 0.5, 0.84], levels=[0.68, 0.95],
            color='C1', nbin=20, smooth=True, fig=fig) 
    _ffig = os.path.join(dir_doc, '_speculator_fsps.prosterior_comparison.png') 
    fig.savefig(_ffig, bbox_inches='tight') 
    return None 


def mini_mocha_comparison(sim='lgal', method='ifsps', model=None, sfr='100myr'):
    ''' ultimate comparison between the different SED fitting methods 
    '''
    if sfr == '100myr': dt = 0.1
    ngal = 97
    sims = ['lgal', 'tng'] 
    
    Mstar_inputs, logSFR_inputs = [], [] 
    Mstar_infs, logSFR_infs = [], [] 
    for sim in sims: 
        # read noiseless Lgal spectra of the spectral_challenge mocks
        specs, meta = Data.Spectra(sim=sim, noise='bgs0', lib='bc03', sample='mini_mocha') 
        # read Lgal photometry of the mini_mocha mocks
        photo, _ = Data.Photometry(sim=sim, noise='legacy', lib='bc03', sample='mini_mocha')
        
        if method == 'ifsps': ifitter = Fitters.iFSPS()
        elif method == 'ispeculator': ifitter = Fitters.iSpeculator()

        igals, theta_inf = [], [] 
        for igal in range(ngal):  
            _fbf = Fbestfit_specphoto(igal, sim=sim, noise='bgs0_legacy',
                    method=method, model=model)
            if not os.path.isfile(_fbf): 
                print('     %s does not exist' % _fbf)
                continue 
            fbf = h5py.File(_fbf, 'r')  
            mcmc_chain = fbf['mcmc_chain'][...].copy() 
            fbf.close() 

            _theta_inf = np.percentile(mcmc_chain, [2.5, 16, 50, 84, 97.5], axis=0)

            igals.append(igal) 
            theta_inf.append(_theta_inf) 

        igals = np.array(igals)

        # input properties 
        Mstar_input = [meta['logM_total'][i] for i in igals] # total mass 
        logSFR_input= np.log10([meta['sfr_%s' % sfr][i] for i in igals])

        # inferred properties
        Mstar_inf   = np.array([_tt[:,0] for _tt in theta_inf])
        logSFR_inf  = np.array([_tt[:,-1] for _tt in theta_inf])

        Mstar_inputs.append(Mstar_input) 
        logSFR_inputs.append(logSFR_input) 
        
        Mstar_infs.append(Mstar_inf) 
        logSFR_infs.append(logSFR_inf) 
    
    fig = plt.figure(figsize=(8,8))
    for i in range(len(sims)):
        Mstar_input = Mstar_inputs[i] 
        Mstar_inf = Mstar_infs[i]
        logSFR_input = logSFR_inputs[i]
        logSFR_inf = logSFR_infs[i]

        # compare total stellar mass 
        sub = fig.add_subplot(2,2,2*i+1) 
        sub.errorbar(Mstar_input, Mstar_inf[:,2], 
                yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
        sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
        sub.text(0.05, 0.95, sims[i].upper(), ha='left', va='top', transform=sub.transAxes, fontsize=25)

        sub.set_xlim(9., 12.) 
        if i == 0: sub.set_xticklabels([])
        sub.set_ylim(9., 12.) 
        sub.set_yticks([9., 10., 11., 12.]) 
        if i == 0: sub.set_title(r'$\log M_*$', fontsize=25)

        # compare SFR 
        sub = fig.add_subplot(2,2,2*i+2) 
        sub.errorbar(logSFR_input, logSFR_inf[:,2], 
                yerr=[logSFR_inf[:,2]-logSFR_inf[:,1], logSFR_inf[:,3]-logSFR_inf[:,2]], fmt='.C0')
        sub.plot([-3., 2.], [-3., 2.], c='k', ls='--') 
        sub.set_xlim(-3., 2.) 
        if i == 0: sub.set_xticklabels([])
        sub.set_ylim(-3., 2.) 
        sub.set_yticks([-2., 0., 2.]) 
        if sfr == '1gyr': lbl_sfr = '1Gyr'
        elif sfr == '100myr': lbl_sfr = r'100{\rm Myr}'
        if i == 0: sub.set_title(r'$\log{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)

    bkgd = fig.add_subplot(111, frameon=False)
    bkgd.set_xlabel(r'$\theta_{\rm true}$', fontsize=25) 
    bkgd.set_ylabel(r'$\widehat{\theta}$', labelpad=10, fontsize=25) 
    bkgd.tick_params(labelcolor='none', top=False, bottom=False, left=False, right=False)
    fig.subplots_adjust(wspace=0.225, hspace=0.1)
    _ffig = os.path.join(dir_doc, 'mini_mocha.%s.%s.sfr_%s.comparison.png' %
            (method, model, sfr)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def mock_challenge_photo(noise='none', dust=False, method='ifsps'): 
    ''' Compare properties inferred from forward modeled photometry to input properties
    '''
    # read Lgal input input properties
    _, meta = Data.Photometry(sim='lgal', noise=noise, lib='bc03', sample='spectral_challenge') 
    Mstar_input = meta['logM_total'] # total mass 
    Z_MW_input  = meta['Z_MW'] # mass-weighted metallicity
    tage_input  = meta['t_age_MW'] # mass-weighted age
    
    theta_inf = [] 
    for igal in range(97): 
        # read best-fit file and get inferred parameters
        _fbf = Fbestfit_photo(igal, noise=noise, dust=dust, method=method) 
        fbf = h5py.File(_fbf, 'r')  

        theta_inf_i = np.array([
            fbf['theta_2sig_minus'][...], 
            fbf['theta_1sig_minus'][...], 
            fbf['theta_med'][...], 
            fbf['theta_1sig_plus'][...], 
            fbf['theta_2sig_plus'][...]])
        theta_inf.append(theta_inf_i) 
    theta_inf = np.array(theta_inf) 
    
    # inferred properties
    Mstar_inf   = theta_inf[:,:,0]
    Z_MW_inf    = 10**theta_inf[:,:,1]
    tage_inf    = theta_inf[:,:,2]
    
    fig = plt.figure(figsize=(15,4))
    # compare total stellar mass 
    sub = fig.add_subplot(131) 
    sub.errorbar(Mstar_input, Mstar_inf[:,2], 
            yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
    sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
    sub.set_xlabel(r'input $\log~M_{\rm tot}$', fontsize=25)
    sub.set_xlim(9., 12.) 
    sub.set_ylabel(r'inferred $\log~M_{\rm tot}$', fontsize=25)
    sub.set_ylim(9., 12.) 
    
    # compare metallicity
    sub = fig.add_subplot(132)
    sub.errorbar(Z_MW_input, Z_MW_inf[:,2], 
            yerr=[Z_MW_inf[:,2]-Z_MW_inf[:,1], Z_MW_inf[:,3]-Z_MW_inf[:,2]], fmt='.C0')
    sub.plot([1e-3, 1], [1e-3, 1.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $Z$', fontsize=20)
    sub.set_xscale('log') 
    sub.set_xlim(1e-3, 5e-2) 
    sub.set_ylabel(r'inferred MW $Z$', fontsize=20)
    sub.set_yscale('log') 
    sub.set_ylim(1e-3, 5e-2) 

    # compare age 
    sub = fig.add_subplot(133)
    sub.errorbar(tage_input, tage_inf[:,2], 
            yerr=[tage_inf[:,2]-tage_inf[:,1], tage_inf[:,3]-tage_inf[:,2]], fmt='.C0')
    sub.plot([0, 13], [0, 13.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $t_{\rm age}$', fontsize=20)
    sub.set_xlim(0, 13) 
    sub.set_ylabel(r'inferred MW $t_{\rm age}$', fontsize=20)
    sub.set_ylim(0, 13) 

    fig.subplots_adjust(wspace=0.4)
    _ffig = os.path.join(dir_fig, 'mock_challenge.photofit.%s.noise_%s.dust_%s.png' % (method, noise, ['no', 'yes'][dust]))
    fig.savefig(_ffig, bbox_inches='tight') 
    return None 


def mini_mocha_spec(noise='bgs0', method='ifsps', sfr='1gyr'): 
    ''' Compare properties inferred from forward modeled photometry to input properties
    '''
    # read noiseless Lgal spectra of the spectral_challenge mocks
    specs, meta = Data.Spectra(sim='lgal', noise=noise, lib='bc03', sample='mini_mocha') 

    Mstar_input = meta['logM_fiber'][:97] # total mass 
    logSFR_input= np.log10(meta['sfr_%s' % sfr][:97])
    Z_MW_input  = meta['Z_MW'][:97]  # mass-weighted metallicity
    tage_input  = meta['t_age_MW'][:97]  # mass-weighted age
    
    theta_inf = [] 
    for igal in range(97): 
        # read best-fit file and get inferred parameters
        _fbf = Fbestfit_spec(igal, noise=noise, method=method) 
        fbf = h5py.File(_fbf, 'r')  

        theta_inf_i = np.array([
            fbf['theta_2sig_minus'][...], 
            fbf['theta_1sig_minus'][...], 
            fbf['theta_med'][...], 
            fbf['theta_1sig_plus'][...], 
            fbf['theta_2sig_plus'][...]])
        
        if method == 'ifsps': 
            ifsps = Fitters.iFSPS()
        if sfr == '1gyr': 
            sfr_inf = ifsps._SFR_MCMC(fbf['mcmc_chain'][...], dt=1.)
        elif sfr == '100myr': 
            sfr_inf = ifsps._SFR_MCMC(fbf['mcmc_chain'][...], dt=0.1)
        theta_inf_i = np.concatenate([theta_inf_i, np.atleast_2d(sfr_inf).T], axis=1) 

        theta_inf.append(theta_inf_i) 
    theta_inf = np.array(theta_inf) 
    
    # inferred properties
    Mstar_inf   = theta_inf[:,:,0]
    logSFR_inf  = np.log10(theta_inf[:,:,-1]) 
    Z_MW_inf    = 10**theta_inf[:,:,1]
    tage_inf    = theta_inf[:,:,2]
    
    fig = plt.figure(figsize=(20,4))
    # compare total stellar mass 
    sub = fig.add_subplot(141) 
    sub.errorbar(Mstar_input, Mstar_inf[:,2], 
            yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
    sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
    sub.set_xlabel(r'input $\log~M_{\rm fib.}$', fontsize=25)
    sub.set_xlim(9., 12.) 
    sub.set_ylabel(r'inferred $\log~M_{\rm fib.}$', fontsize=25)
    sub.set_ylim(9., 12.) 

    # compare SFR
    sub = fig.add_subplot(142) 
    sub.errorbar(logSFR_input, logSFR_inf[:,2], 
            yerr=[logSFR_inf[:,2]-logSFR_inf[:,1], logSFR_inf[:,3]-logSFR_inf[:,2]], fmt='.C0')
    sub.plot([-3., 2.], [-3., 2.], c='k', ls='--') 
    if sfr == '1gyr': lbl_sfr = '1Gyr'
    elif sfr == '100myr': lbl_sfr = '100Myr'
    sub.set_xlabel(r'input $\log~{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    sub.set_xlim(-3., 2.) 
    sub.set_ylabel(r'inferred $\log~{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    sub.set_ylim(-3., 2.) 
    
    # compare metallicity
    sub = fig.add_subplot(143)
    sub.errorbar(Z_MW_input, Z_MW_inf[:,2], 
            yerr=[Z_MW_inf[:,2]-Z_MW_inf[:,1], Z_MW_inf[:,3]-Z_MW_inf[:,2]], fmt='.C0')
    sub.plot([1e-3, 1], [1e-3, 1.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $Z$', fontsize=20)
    sub.set_xscale('log') 
    sub.set_xlim(1e-3, 5e-2) 
    sub.set_ylabel(r'inferred MW $Z$', fontsize=20)
    sub.set_yscale('log') 
    sub.set_ylim(1e-3, 5e-2) 

    # compare age 
    sub = fig.add_subplot(144)
    sub.errorbar(tage_input, tage_inf[:,2], 
            yerr=[tage_inf[:,2]-tage_inf[:,1], tage_inf[:,3]-tage_inf[:,2]], fmt='.C0')
    sub.plot([0, 13], [0, 13.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $t_{\rm age}$', fontsize=20)
    sub.set_xlim(0, 13) 
    sub.set_ylabel(r'inferred MW $t_{\rm age}$', fontsize=20)
    sub.set_ylim(0, 13) 

    fig.subplots_adjust(wspace=0.4)
    _ffig = os.path.join(dir_fig, 'mini_mocha.sfr_%s.%s.specfit.vanilla.noise_%s.png' % (sfr, method, noise)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def mini_mocha_photo(noise='legacy', method='ifsps', sfr='1gyr'): 
    ''' Compare properties inferred from forward modeled photometry to input properties
    '''
    # read noiseless Lgal spectra of the spectral_challenge mocks
    photo, meta = Data.Photometry(sim='lgal', noise=noise, lib='bc03', sample='mini_mocha')

    Mstar_input = meta['logM_total'][:97] # total mass 
    logSFR_input= np.log10(meta['sfr_%s' % sfr][:97])
    Z_MW_input  = meta['Z_MW'][:97]  # mass-weighted metallicity
    tage_input  = meta['t_age_MW'][:97]  # mass-weighted age
    
    theta_inf = [] 
    for igal in range(97): 
        # read best-fit file and get inferred parameters
        _fbf = Fbestfit_photo(igal, noise=noise, method=method) 
        fbf = h5py.File(_fbf, 'r')  

        theta_inf_i = np.array([
            fbf['theta_2sig_minus'][...], 
            fbf['theta_1sig_minus'][...], 
            fbf['theta_med'][...], 
            fbf['theta_1sig_plus'][...], 
            fbf['theta_2sig_plus'][...]])
        
        if method == 'ifsps': 
            ifsps = Fitters.iFSPS()
        if sfr == '1gyr': 
            sfr_inf = ifsps._SFR_MCMC(fbf['mcmc_chain'][...], dt=1.)
        elif sfr == '100myr': 
            sfr_inf = ifsps._SFR_MCMC(fbf['mcmc_chain'][...], dt=0.1)
        theta_inf_i = np.concatenate([theta_inf_i, np.atleast_2d(sfr_inf).T], axis=1) 
        theta_inf.append(theta_inf_i) 

    theta_inf = np.array(theta_inf) 
    
    # inferred properties
    Mstar_inf   = theta_inf[:,:,0]
    logSFR_inf  = np.log10(theta_inf[:,:,-1]) 
    Z_MW_inf    = 10**theta_inf[:,:,1]
    tage_inf    = theta_inf[:,:,2]
    
    fig = plt.figure(figsize=(20,4))
    # compare total stellar mass 
    sub = fig.add_subplot(141) 
    sub.errorbar(Mstar_input, Mstar_inf[:,2], 
            yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
    sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
    sub.set_xlabel(r'input $\log~M_{\rm tot.}$', fontsize=25)
    sub.set_xlim(9., 12.) 
    sub.set_ylabel(r'inferred $\log~M_{\rm tot.}$', fontsize=25)
    sub.set_ylim(9., 12.) 
    
    # compare SFR 
    sub = fig.add_subplot(142) 
    sub.errorbar(logSFR_input, logSFR_inf[:,2], 
            yerr=[logSFR_inf[:,2]-logSFR_inf[:,1], logSFR_inf[:,3]-logSFR_inf[:,2]], fmt='.C0')
    sub.plot([-3., 2.], [-3., 2.], c='k', ls='--') 
    if sfr == '1gyr': lbl_sfr = '1Gyr'
    elif sfr == '100myr': lbl_sfr = '100Myr'
    sub.set_xlabel(r'input $\log~{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    sub.set_xlim(-3., 2.) 
    sub.set_ylabel(r'inferred $\log~{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    sub.set_ylim(-3., 2.) 
    
    # compare metallicity
    sub = fig.add_subplot(143)
    sub.errorbar(Z_MW_input, Z_MW_inf[:,2], 
            yerr=[Z_MW_inf[:,2]-Z_MW_inf[:,1], Z_MW_inf[:,3]-Z_MW_inf[:,2]], fmt='.C0')
    sub.plot([1e-3, 1], [1e-3, 1.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $Z$', fontsize=20)
    sub.set_xscale('log') 
    sub.set_xlim(1e-3, 5e-2) 
    sub.set_ylabel(r'inferred MW $Z$', fontsize=20)
    sub.set_yscale('log') 
    sub.set_ylim(1e-3, 5e-2) 

    # compare age 
    sub = fig.add_subplot(144)
    sub.errorbar(tage_input, tage_inf[:,2], 
            yerr=[tage_inf[:,2]-tage_inf[:,1], tage_inf[:,3]-tage_inf[:,2]], fmt='.C0')
    sub.plot([0, 13], [0, 13.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $t_{\rm age}$', fontsize=20)
    sub.set_xlim(0, 13) 
    sub.set_ylabel(r'inferred MW $t_{\rm age}$', fontsize=20)
    sub.set_ylim(0, 13) 

    fig.subplots_adjust(wspace=0.4)
    _ffig = os.path.join(dir_fig, 'mini_mocha.sfr_%s.%s.photofit.vanilla.noise_%s.png' % (sfr, method, noise)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def mini_mocha_specphoto(noise='bgs0_legacy', method='ifsps', sfr='1gyr'): 
    ''' Compare properties inferred from forward modeled photometry to input properties
    '''
    if noise != 'none':
        noise_spec = noise.split('_')[0]
        noise_photo = noise.split('_')[1]
    else:
        noise_spec = 'none'
        noise_photo = 'none'
    # read noiseless Lgal spectra of the spectral_challenge mocks
    specs, meta = Data.Spectra(sim='lgal', noise=noise_spec, lib='bc03', sample='mini_mocha') 
    # read Lgal photometry of the mini_mocha mocks
    photo, _ = Data.Photometry(sim='lgal', noise=noise_photo, lib='bc03', sample='mini_mocha')

    Mstar_input = meta['logM_total'][:97] # total mass 
    logSFR_input= np.log10(meta['sfr_%s' % sfr][:97])
    Z_MW_input  = meta['Z_MW'][:97]  # mass-weighted metallicity
    tage_input  = meta['t_age_MW'][:97]  # mass-weighted age
    
    theta_inf = [] 
    for igal in range(97): 
        # read best-fit file and get inferred parameters
        _fbf = Fbestfit_specphoto(igal, noise=noise, method=method) 
        fbf = h5py.File(_fbf, 'r')  

        theta_inf_i = np.array([
            fbf['theta_2sig_minus'][...], 
            fbf['theta_1sig_minus'][...], 
            fbf['theta_med'][...], 
            fbf['theta_1sig_plus'][...], 
            fbf['theta_2sig_plus'][...]])
        if method == 'ifsps': 
            ifsps = Fitters.iFSPS()
        if sfr == '1gyr': 
            sfr_inf = ifsps._SFR_MCMC(fbf['mcmc_chain'][...], dt=1.)
        elif sfr == '100myr': 
            sfr_inf = ifsps._SFR_MCMC(fbf['mcmc_chain'][...], dt=0.1)
        theta_inf_i = np.concatenate([theta_inf_i, np.atleast_2d(sfr_inf).T], axis=1) 

        theta_inf.append(theta_inf_i) 
    theta_inf = np.array(theta_inf) 
    
    # inferred properties
    Mstar_inf   = theta_inf[:,:,0]
    logSFR_inf  = np.log10(theta_inf[:,:,-1]) 
    Z_MW_inf    = 10**theta_inf[:,:,1]
    tage_inf    = theta_inf[:,:,2]
    
    fig = plt.figure(figsize=(20,4))
    # compare total stellar mass 
    sub = fig.add_subplot(141) 
    sub.errorbar(Mstar_input, Mstar_inf[:,2], 
            yerr=[Mstar_inf[:,2]-Mstar_inf[:,1], Mstar_inf[:,3]-Mstar_inf[:,2]], fmt='.C0')
    sub.plot([9., 12.], [9., 12.], c='k', ls='--') 
    sub.set_xlabel(r'input $\log~M_{\rm tot}$', fontsize=25)
    sub.set_xlim(9., 12.) 
    sub.set_ylabel(r'inferred $\log~M_{\rm tot}$', fontsize=25)
    sub.set_ylim(9., 12.) 
    
    # compare SFR 
    sub = fig.add_subplot(142) 
    sub.errorbar(logSFR_input, logSFR_inf[:,2], 
            yerr=[logSFR_inf[:,2]-logSFR_inf[:,1], logSFR_inf[:,3]-logSFR_inf[:,2]], fmt='.C0')
    sub.plot([-3., 2.], [-3., 2.], c='k', ls='--') 
    if sfr == '1gyr': lbl_sfr = '1Gyr'
    elif sfr == '100myr': lbl_sfr = '100Myr'
    sub.set_xlabel(r'input $\log~{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    sub.set_xlim(-3., 2.) 
    sub.set_ylabel(r'inferred $\log~{\rm SFR}_{%s}$' % lbl_sfr, fontsize=25)
    sub.set_ylim(-3., 2.) 
    
    # compare metallicity
    sub = fig.add_subplot(143)
    sub.errorbar(Z_MW_input, Z_MW_inf[:,2], 
            yerr=[Z_MW_inf[:,2]-Z_MW_inf[:,1], Z_MW_inf[:,3]-Z_MW_inf[:,2]], fmt='.C0')
    sub.plot([1e-3, 1], [1e-3, 1.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $Z$', fontsize=20)
    sub.set_xscale('log') 
    sub.set_xlim(1e-3, 5e-2) 
    sub.set_ylabel(r'inferred MW $Z$', fontsize=20)
    sub.set_yscale('log') 
    sub.set_ylim(1e-3, 5e-2) 

    # compare age 
    sub = fig.add_subplot(144)
    sub.errorbar(tage_input, tage_inf[:,2], 
            yerr=[tage_inf[:,2]-tage_inf[:,1], tage_inf[:,3]-tage_inf[:,2]], fmt='.C0')
    sub.plot([0, 13], [0, 13.], c='k', ls='--') 
    sub.set_xlabel(r'input MW $t_{\rm age}$', fontsize=20)
    sub.set_xlim(0, 13) 
    sub.set_ylabel(r'inferred MW $t_{\rm age}$', fontsize=20)
    sub.set_ylim(0, 13) 

    fig.subplots_adjust(wspace=0.4)
    _ffig = os.path.join(dir_fig, 'mini_mocha.sfr_%s.%s.specphotofit.vanilla.noise_%s.png' % (sfr, method, noise)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def photo_vs_specphoto(sim='lgal', noise_photo='legacy', noise_specphoto='bgs0_legacy',
        method='ifsps', model='vanilla', sample='mini_mocha'):  
    ''' Compare properties inferred from photometry versus spectrophotometry to see how much
    information is gained from adding spectra
    '''
    # read noiseless Lgal spectra of the spectral_challenge mocks
    _, meta = Data.Spectra(sim=sim, noise=noise_photo, lib='bc03', sample='mini_mocha') 
    logMstar_sim  = np.array(meta['logM_total']) # total mass 
    logSFR_sim    = np.log10(np.array(meta['sfr_100myr'])) 
    if sim == 'tng': 
        print('correcting for possible h?') 
        logMstar_sim += np.log10(1./0.6774**2)
        logSFR_sim += np.log10(1./0.6774**2)
    # --------------------------------------------------------------------------------
    # compile MC chains 
    _igal0, _dlogMs_photo = _read_dprop_mcmc('logmstar', obs='photo', sim=sim, 
            noise=noise_photo, method=method, model=model, sample=sample)
    _igal1, _dlogMs_specphoto = _read_dprop_mcmc('logmstar', obs='specphoto', sim=sim, 
            noise=noise_specphoto, method=method, model=model, sample=sample)
    igal_m, m0, m1 = np.intersect1d(_igal0, _igal1, return_indices=True) 
    logm_input      = logMstar_sim[igal_m]
    dlogm_photo     = _dlogMs_photo[m0]
    dlogm_specphoto = _dlogMs_specphoto[m1]
    
    _igal0, _dlogSFRs_photo = _read_dprop_mcmc('logsfr.100myr', sim=sim,
            obs='photo', noise=noise_photo, method=method, model=model,
            sample=sample) 
    _igal1, _dlogSFRs_specphoto = _read_dprop_mcmc('logsfr.100myr', sim=sim, 
            obs='specphoto', noise=noise_specphoto, method=method, model=model,
            sample=sample) 
    igal_s, m0, m1 = np.intersect1d(_igal0, _igal1, return_indices=True) 
    logsfr_input        = logSFR_sim[igal_s]
    dlogsfr_photo       = _dlogSFRs_photo[m0]
    dlogsfr_specphoto   = _dlogSFRs_specphoto[m1]
    # --------------------------------------------------------------------------------
    # maximum likelihood for the population hyperparameters
    bins_logm = np.linspace(9., 12., 7) 
    logm_mid, eta_logm_photo   = _get_etaMAP(logm_input, dlogm_photo, bins_logm)
    logm_mid, eta_logm_specphoto  = _get_etaMAP(logm_input, dlogm_specphoto, bins_logm)
    
    bins_logsfr = np.linspace(-3., 3., 7) 
    logsfr_mid, eta_logsfr_photo   = _get_etaMAP(logsfr_input, dlogsfr_photo, bins_logsfr)
    logsfr_mid, eta_logsfr_specphoto  = _get_etaMAP(logsfr_input, dlogsfr_specphoto, bins_logsfr)
    # --------------------------------------------------------------------------------
    fig = plt.figure(figsize=(12,5))
    # compare total stellar mass 
    sub = fig.add_subplot(121) 
    sub.plot([9., 12.], [0., 0.], c='k', ls='--')
    sub.fill_between(logm_mid, 
            eta_logm_photo[:,0] - eta_logm_photo[:,1],
            eta_logm_photo[:,0] + eta_logm_photo[:,1], 
            fc='C0', ec='none', alpha=0.5, label='Photometry only') 
    sub.scatter(logm_mid, eta_logm_photo[:,0], c='C0', s=2) 
    sub.plot(logm_mid, eta_logm_photo[:,0], c='C0')
    sub.fill_between(logm_mid, 
            eta_logm_specphoto[:,0] - eta_logm_specphoto[:,1],
            eta_logm_specphoto[:,0] + eta_logm_specphoto[:,1], 
            fc='C1', ec='none', alpha=0.5, label='Photometry+Spectroscopy') 
    sub.scatter(logm_mid, eta_logm_specphoto[:,0], c='C1', s=1) 
    sub.plot(logm_mid, eta_logm_specphoto[:,0], c='C1') 
    sub.set_xlabel(r'$\log(~M_*~[M_\odot]~)$', fontsize=25)
    sub.set_xlim(9., 12.) 
    sub.set_ylabel(r'$\Delta_{\log M_*}$', fontsize=25)
    sub.set_ylim(-1., 1.) 
    sub.legend(loc='upper right', fontsize=20, handletextpad=0.2) 
    
    # compare SFR 
    sub = fig.add_subplot(122) 
    sub.plot([-3., 3.], [0., 0.], c='k', ls='--')
    sub.fill_between(logsfr_mid,  
            eta_logsfr_photo[:,0] - eta_logsfr_photo[:,1],
            eta_logsfr_photo[:,0] + eta_logsfr_photo[:,1], 
            fc='C0', ec='none', alpha=0.5) 
    sub.scatter(logsfr_mid, eta_logsfr_photo[:,0], c='C0', s=2) 
    sub.plot(logsfr_mid, eta_logsfr_photo[:,0], c='C0') 
    sub.fill_between(logsfr_mid,
            eta_logsfr_specphoto[:,0] - eta_logsfr_specphoto[:,1],
            eta_logsfr_specphoto[:,0] + eta_logsfr_specphoto[:,1], 
            fc='C1', ec='none', alpha=0.5) 
    sub.scatter(logsfr_mid, eta_logsfr_specphoto[:,0], c='C1', s=1) 
    sub.plot(logsfr_mid, eta_logsfr_specphoto[:,0], c='C1') 
    
    sub.set_xlabel(r'$\log(~{\rm SFR}_{100Myr}~[M_\odot/yr]~)$', fontsize=25)
    sub.set_xlim(-3., 1.) 
    sub.set_ylabel(r'$\Delta_{\log{\rm SFR}_{100Myr}}$', fontsize=25)
    sub.set_ylim(-3., 3.) 
    
    fig.subplots_adjust(wspace=0.3)
    _ffig = os.path.join(dir_doc,
            'photo_vs_specphoto.%s.%s.%s.noise_%s_%s.png' % 
            (sim, method, model, noise_photo, noise_specphoto)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def dust_comparison(sim='lgal', noise='bgs0_legacy', method='ifsps'): 
    ''' Compare properties inferred from photometry versus spectrophotometry to see how much
    information is gained from adding spectra
    '''
    # read noiseless Lgal spectra of the spectral_challenge mocks
    _, meta = Data.Spectra(sim=sim, noise=noise.split('_')[0], lib='bc03', sample='mini_mocha') 
    logMstar_sim  = np.array(meta['logM_total']) # total mass 
    logSFR_sim    = np.log10(np.array(meta['sfr_100myr'])) 
    # --------------------------------------------------------------------------------
    # compile MC chains 
    _igal0, _dlogMs_simple = _read_dprop_mcmc('logmstar', obs='specphoto', noise=noise,
            method='ifsps', model='vanilla', sample='mini_mocha')
    _igal1, _dlogMs_complex = _read_dprop_mcmc('logmstar', obs='specphoto', noise=noise,
            method='ifsps', model='vanilla_complexdust', sample='mini_mocha')
    igal_m, m0, m1 = np.intersect1d(_igal0, _igal1, return_indices=True) 
    logm_input      = logMstar_sim[igal_m]
    dlogm_simple    = _dlogMs_simple[m0]
    dlogm_complex   = _dlogMs_complex[m1]
    
    _igal0, _dlogSFRs_simple = _read_dprop_mcmc('logsfr.100myr', sim=sim,
            obs='specphoto', noise=noise, method=method, model='vanilla',
            sample='mini_mocha') 
    _igal1, _dlogSFRs_complex = _read_dprop_mcmc('logsfr.100myr', sim=sim, 
            obs='specphoto', noise=noise, method=method,
            model='vanilla_complexdust', sample='mini_mocha')
    igal_s, m0, m1 = np.intersect1d(_igal0, _igal1, return_indices=True) 
    logsfr_input    = logSFR_sim[igal_s]
    dlogsfr_simple  = _dlogSFRs_simple[m0]
    dlogsfr_complex = _dlogSFRs_complex[m1]
    # --------------------------------------------------------------------------------
    # maximum likelihood for the population hyperparameters
    bins_logm = np.linspace(9., 12., 7) 
    logm_mid, eta_logm_simple   = _get_etaMAP(logm_input, dlogm_simple, bins_logm)
    logm_mid, eta_logm_complex  = _get_etaMAP(logm_input, dlogm_complex, bins_logm)
    
    bins_logsfr = np.linspace(-3., 3., 7) 
    logsfr_mid, eta_logsfr_simple   = _get_etaMAP(logsfr_input, dlogsfr_simple, bins_logsfr)
    logsfr_mid, eta_logsfr_complex  = _get_etaMAP(logsfr_input, dlogsfr_complex, bins_logsfr)

    # --------------------------------------------------------------------------------
    fig = plt.figure(figsize=(12,5))
    # compare log M*
    sub = fig.add_subplot(121) 
    sub.plot([9., 12.], [0., 0.], c='k', ls='--')
    sub.fill_between(logm_mid, eta_logm_simple[:,0] - eta_logm_simple[:,1], eta_logm_simple[:,0] + eta_logm_simple[:,1],
            fc='C0', ec='none', alpha=0.5, label='Simple Dust') 
    sub.scatter(logm_mid, eta_logm_simple[:,0], c='C0', s=2) 
    sub.plot(logm_mid, eta_logm_simple[:,0], c='C0')
    sub.fill_between(logm_mid, eta_logm_complex[:,0] - eta_logm_complex[:,1], eta_logm_complex[:,0] + eta_logm_complex[:,1], 
            fc='C1', ec='none', alpha=0.5, label='Complex Dust') 
    sub.scatter(logm_mid, eta_logm_complex[:,0], c='C1', s=1) 
    sub.plot(logm_mid, eta_logm_complex[:,0], c='C1') 
    sub.set_xlabel(r'$\log(~M_*~[M_\odot]~)$', fontsize=25)
    sub.set_xlim(9., 12.) 
    sub.set_ylabel(r'$\Delta_{\log M_*}$', fontsize=25)
    sub.set_ylim(-1., 1.) 
    sub.legend(loc='upper right', fontsize=20, handletextpad=0.2) 
    
    # compare log SFR 
    sub = fig.add_subplot(122) 
    sub.plot([-3., 3.], [0., 0.], c='k', ls='--')
    sub.fill_between(logsfr_mid, 
            eta_logsfr_simple[:,0] - eta_logsfr_simple[:,1], 
            eta_logsfr_simple[:,0] + eta_logsfr_simple[:,1],
            fc='C0', ec='none', alpha=0.5) 
    sub.scatter(logsfr_mid, eta_logsfr_simple[:,0], c='C0', s=2) 
    sub.plot(logsfr_mid, eta_logsfr_simple[:,0], c='C0') 
    sub.fill_between(logsfr_mid, 
            eta_logsfr_complex[:,0] - eta_logsfr_complex[:,1], 
            eta_logsfr_complex[:,0] + eta_logsfr_complex[:,1],
            fc='C1', ec='none', alpha=0.5) 
    sub.scatter(logsfr_mid, eta_logsfr_complex[:,0], c='C1', s=2) 
    sub.plot(logsfr_mid, eta_logsfr_complex[:,0], c='C1') 

    sub.set_xlabel(r'$\log(~{\rm SFR}_{100Myr}~[M_\odot/yr]~)$', fontsize=25)
    sub.set_xlim(-3., 2.) 
    sub.set_ylabel(r'$\Delta_{\log{\rm SFR}_{100Myr}}$', fontsize=25)
    sub.set_ylim(-3., 3.) 
    
    fig.subplots_adjust(wspace=0.3)
    _ffig = os.path.join(dir_doc,
            'dust_comparison.%s.%s.noise_%s.png' % (sim, method, noise)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def eta_Delta(sim='lgal', noise='bgs0_legacy', method='ifsps', model='vanilla',
        sample='mini_mocha'):  
    ''' population hyperparameters eta_Delta as a function of different
    galaxy properties (r mag, color, etc) 
    '''
    # --------------------------------------------------------------------------------
    # read noiseless Lgal spectra of the spectral_challenge mocks
    specs, meta = Data.Spectra(sim=sim, noise=noise.split('_')[0], lib='bc03', sample='mini_mocha') 
    # read Lgal photometry of the mini_mocha mocks
    photo, _ = Data.Photometry(sim=sim, noise=noise.split('_')[1], lib='bc03', sample='mini_mocha')
    # --------------------------------------------------------------------------------
    # true paramater values
    # --------------------------------------------------------------------------------
    logMstar_all    = np.array(meta['logM_total']) # total mass 
    logSFR_all      = np.log10(np.array(meta['sfr_100myr'])) 

    r_mag   = 22.5 - 2.5 * np.log10(photo['flux_r_true']) # true r-band magnitude
    g_r     = (22.5 - 2.5 * np.log10(photo['flux_g_true'])) - r_mag 
    r_z     = r_mag - (22.5 - 2.5 * np.log10(photo['flux_z_true']))
    # --------------------------------------------------------------------------------
    # assemble all markov chains 
    # --------------------------------------------------------------------------------
    igal_m, dlogm_chain = _read_dprop_mcmc('logmstar', sim=sim,
            obs='specphoto', noise=noise, method=method, model=model,
            sample=sample)
    igal_s, dlogsfr_chain = _read_dprop_mcmc('logsfr.100myr', sim=sim, 
            obs='specphoto', noise=noise, method=method, model=model,
            sample=sample)
    # --------------------------------------------------------------------------------
    # get MAP for the population hyperparameters
    # --------------------------------------------------------------------------------
    props       = [r_mag, g_r, r_z]
    prop_lbl    = ['$r$ magnitude', '$g - r$ color', '$r - z$ color']
    prop_lim    = [(19, 20), (0., 2.), (0., 1.)]
    
    hyper_logm, hyper_logsfr = [], [] 
    for i, prop in enumerate(props) : 
        bins_prop = np.linspace(prop_lim[i][0], prop_lim[i][1], 11) 

        mid_prop_m, eta_logm    = _get_etaMAP(prop[igal_m], dlogm_chain, bins_prop)
        mid_prop_s, eta_logsfr  = _get_etaMAP(prop[igal_s], dlogsfr_chain, bins_prop)

        hyper_logm.append([mid_prop_m, eta_logm[:,0], eta_logm[:,1]]) 
        hyper_logsfr.append([mid_prop_s, eta_logsfr[:,0], eta_logsfr[:,1]]) 
    # --------------------------------------------------------------------------------
    # plot the MAP hyperparameters
    # --------------------------------------------------------------------------------
    fig = plt.figure(figsize=(4*len(props),8))
    for i in range(len(props)): 

        prop_mid_m, mu_dmstar, sig_dmstar = hyper_logm[i]
        prop_mid_s, mu_dsfr, sig_dsfr = hyper_logsfr[i]

        # M* hyperparametrs
        sub = fig.add_subplot(2,len(props),i+1) 

        sub.plot([prop_lim[i][0], prop_lim[i][1]], [0., 0.], c='k', ls='--')
        sub.fill_between(prop_mid_m, mu_dmstar - sig_dmstar, mu_dmstar + sig_dmstar, 
                fc='C0', ec='none', alpha=0.5) 
        sub.scatter(prop_mid_m, mu_dmstar, c='C0', s=2) 
        sub.plot(prop_mid_m, mu_dmstar, c='C0') 

        sub.set_xlim(prop_lim[i][0], prop_lim[i][1]) 
        if i == 0: sub.set_ylabel(r'$\Delta_{\log M_*}$', fontsize=25)
        sub.set_ylim(-1., 1.) 
        #sub.legend(loc='upper right', fontsize=20, handletextpad=0.2) 
    
        # SFR hyperparametrs
        sub = fig.add_subplot(2,len(props),len(props)+i+1) 
        sub.plot([prop_lim[i][0], prop_lim[i][1]], [0., 0.], c='k', ls='--')
        sub.fill_between(prop_mid_s, mu_dsfr - sig_dsfr, mu_dsfr + sig_dsfr, 
                fc='C0', ec='none', alpha=0.5) 
        sub.scatter(prop_mid_s, mu_dsfr, c='C0', s=2) 
        sub.plot(prop_mid_s, mu_dsfr, c='C0') 
        
        sub.set_xlabel(prop_lbl[i], fontsize=25)
        sub.set_xlim(prop_lim[i][0], prop_lim[i][1]) 
        if i == 0: sub.set_ylabel(r'$\Delta_{\log{\rm SFR}_{100Myr}}$', fontsize=25)
        sub.set_ylim(-3., 3.) 
    
    fig.subplots_adjust(wspace=0.3)
    _ffig = os.path.join(dir_doc, 'eta_Delta.%s.%s.%s.noise_%s.png' % (sim, method, model, noise)) 
    fig.savefig(_ffig, bbox_inches='tight') 
    fig.savefig(UT.fig_tex(_ffig, pdf=True), bbox_inches='tight') 
    return None 


def logL_pop(mu_pop, sigma_pop, delta_chains=None, prior=None): 
    ''' log likelihood of population variables mu, sigma
    
    :param mu_pop: 

    :param sigma_pop: 

    :param delta_chains: (default: None) 
        Ngal x Niter 

    :param prior: (default: None) 
        prior function  
    '''
    if prior is None: prior = lambda x: 1. # uninformative prior default 

    N = delta_chains.shape[0] 

    logp_D_pop = 0. 
    for i in range(N): 
        K = len(delta_chains[i]) 
        gauss = Norm(loc=mu_pop, scale=sigma_pop) 
    
        if np.any(np.isnan(delta_chains[i])): 
            p_Di_pop = 0.
        else: 
            p_Di_pop = np.sum(gauss.pdf(delta_chains[i])/prior(delta_chains[i]))/float(K)

        # clip likelihood at 1e-8 
        logp_D_pop += np.log(np.clip(p_Di_pop, 1e-8, None)) 

    if np.isnan(logp_D_pop): 
        for i in range(N): 
            K = len(delta_chains[i]) 
            print(i)
            gauss = Norm(loc=mu_pop, scale=sigma_pop) 
            print('mu:', mu_pop, 'sigma:', sigma_pop) 
            print(delta_chains[i]) 
            p_Di_pop = np.sum(gauss.pdf(delta_chains[i])/prior(delta_chains[i]))/float(K)
            print(p_Di_pop) 
        raise ValueError
    return logp_D_pop     


def _get_etaMAP(prop, chain, bins): 
    ''' get MAP hyperparameters
    '''
    assert len(prop) == chain.shape[0]

    # optimization kwargs
    opt_kwargs = {'method': 'L-BFGS-B', 'bounds': ((None, None), (1e-4, None))}
    #, options={'eps': np.array([0.01, 0.005]), 'maxiter': 100})

    bin_mid, eta = [], [] 
    for i in range(len(bins)-1): 
        inbin = (prop > bins[i]) & (prop <= bins[i+1]) 
        if np.sum(inbin) == 0: continue 
       
        bin_mid.append(0.5 * (bins[i] + bins[i+1])) 

        L_pop = lambda _theta: -1.*logL_pop(_theta[0], _theta[1],
                delta_chains=chain[inbin])  

        _min = op.minimize(L_pop, np.array([0., 0.1]), **opt_kwargs) 

        eta.append([_min['x'][0], _min['x'][1]]) 

    return np.array(bin_mid), np.array(eta)


def _read_dprop_mcmc(prop, sim='lgal', obs='specphoto', noise='bgs0_legacy',
        method='ispeculator', model='emulator', sample='mini_mocha'): 
    ''' read prop_inf - prop_input for MC chains 
    '''
    # --------------------------------------------------------------------------------
    # read noiseless Lgal spectra of the spectral_challenge mocks
    _, meta = Data.Spectra(sim=sim, noise='bgs0',
            lib='bc03', sample=sample) 
    if prop == 'logmstar': 
        prop_sim = np.array(meta['logM_total']) # total mass 
    elif prop == 'logsfr.100myr': 
        prop_sim = np.log10(np.array(meta['sfr_100myr'])) 

    if sim == 'tng': 
        print('correcting for possible h?') 
        prop_sim += np.log10(1./0.6774**2)
    # --------------------------------------------------------------------------------
    if obs == 'specphoto': 
        Fbestfit = Fbestfit_specphoto
    elif obs == 'photo':
        Fbestfit = Fbestfit_photo
    # --------------------------------------------------------------------------------
    # assemble all markov chains 
    igals, dprop = [], [] 
    for igal in range(97): 
        # read best-fit file and get inferred parameters from photometry
        _fbf = Fbestfit(igal, sim=sim, noise=noise, method=method,
                model=model) 
        
        if not os.path.isfile(_fbf): continue 

        fbf = h5py.File(_fbf, 'r')  
        theta_names = list(fbf['theta_names'][...].astype(str)) 
        try: 
            i_prop = theta_names.index(prop) 
        except ValueError: 
            continue 

        chain       = fbf['mcmc_chain'][...][::10]
        dprop_chain = chain[:,i_prop] - prop_sim[igal] 
        
        if np.any(np.isnan(dprop_chain)): continue 

        dprop.append(dprop_chain)
        igals.append(igal) 
    
    return np.array(igals), np.array(dprop)


def Fbestfit_spec(igal, noise='none', method='ifsps'): 
    ''' file name of best-fit of spectra of spectral_challenge galaxy #igal 

    :param igal: 
        index of spectral_challenge galaxy 

    :param noise:
        noise of the spectra. If noise == 'none', no noise. If noise =='bgs0' - 'bgs7', 
        then BGS like noise. (default: 'none') 

    :param dust: 
        spectra has dust or not. 
    
    :param method: 
        fitting method. (default: ifsps)

    '''
    model = 'vanilla'
    if method == 'ifsps': 
        f_bf = os.path.join(UT.dat_dir(), 'mini_mocha', 'ifsps', 'lgal.spec.noise_%s.%s.%i.hdf5' % (noise, model, igal))
    elif method == 'pfirefly': 
        f_bf = os.path.join(UT.dat_dir(), 'mini_mocha', 'pff', 'lgal.spec.noise_%s.%s.%i.hdf5' % (noise, model, igal))
    return f_bf


def Fbestfit_photo(igal, sim='lgal', noise='legacy', method='ifsps', model='vanilla'): 
    ''' file name of best-fit of photometry of spectral_challenge galaxy #igal

    :param igal: 
        index of spectral_challenge galaxy 

    :param noise:
        noise of the spectra. If noise == 'none', no noise. If noise =='legacy', 
        then legacy like noise. (default: 'none') 

    :param dust: 
        spectra has dust or not. 
    
    :param method: 
        fitting method. (default: ifsps)
    '''
    f_bf = os.path.join(UT.dat_dir(), 'mini_mocha', method, 
            '%s.photo.noise_%s.%s.%i.hdf5' % (sim, noise, model, igal))
    return f_bf


def Fbestfit_specphoto(igal, sim='lgal', noise='bgs0_legacy', method='ifsps',
        model='vanilla'): 
    ''' file name of best-fit of photometry of spectral_challenge galaxy #igal

    :param igal: 
        index of spectral_challenge galaxy 

    :param noise:
        noise of the spectra. If noise == 'none', no noise. If noise =='legacy', 
        then legacy like noise. (default: 'none') 

    :param dust: 
        spectra has dust or not. 
    
    :param method: 
        fitting method. (default: ifsps)
    '''
    f_bf = os.path.join(UT.dat_dir(), 'mini_mocha', method, 
            '%s.specphoto.noise_%s.%s.%i.hdf5' % (sim, noise, model, igal))
    return f_bf


if __name__=="__main__": 
    #BGS()
    #FM_photo()
    #FM_spec()
    
    #speculator()
    
    #mcmc_posterior()

    #inferred_props(method='ifsps', model='vanilla', sfr='100myr')
    #inferred_props(method='ispeculator', model='emulator', sfr='100myr')

    #_speculator_fsps(sfr='100myr')

    #photo_vs_specphoto(sim='lgal', noise_photo='legacy', noise_specphoto='bgs0_legacy', 
    #        method='ifsps', model='vanilla')
    #photo_vs_specphoto(sim='tng', noise_photo='legacy', noise_specphoto='bgs0_legacy', 
    #        method='ifsps', model='vanilla')

    photo_vs_specphoto(sim='lgal', noise_photo='legacy', noise_specphoto='bgs0_legacy', 
            method='ispeculator', model='emulator')
    #photo_vs_specphoto(sim='tng', noise_photo='legacy', noise_specphoto='bgs0_legacy', 
    #        method='ispeculator', model='emulator')
    #eta_Delta(sim='lgal', noise='bgs0_legacy', method='ifsps', model='vanilla')
    #eta_Delta(sim='tng', noise='bgs0_legacy', method='ifsps', model='vanilla')
    #eta_Delta(sim='lgal', noise='bgs0_legacy', method='ispeculator', model='emulator')

    #dust_comparison(sim='lgal', noise='bgs0_legacy')


    #mock_challenge_photo(noise='none', dust=False, method='ifsps')
    #mock_challenge_photo(noise='none', dust=True, method='ifsps')
    #mock_challenge_photo(noise='legacy', dust=False, method='ifsps')
    #mock_challenge_photo(noise='legacy', dust=True, method='ifsps')

    #mini_mocha_spec(noise='bgs0', method='ifsps', sfr='1gyr')
    #mini_mocha_spec(noise='bgs0', method='ifsps', sfr='100myr')
    #mini_mocha_photo(noise='legacy', method='ifsps', sfr='1gyr')
    #mini_mocha_photo(noise='legacy', method='ifsps', sfr='100myr')
    #mini_mocha_specphoto(noise='bgs0_legacy', method='ifsps', sfr='1gyr')
    #mini_mocha_specphoto(noise='bgs0_legacy', method='ifsps', sfr='100myr')
    
    #mini_mocha_spec(noise='bgs0', method='pfirefly')
    
