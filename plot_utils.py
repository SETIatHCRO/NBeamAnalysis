'''
plotting utility functions mainly used in plot_DOT_hits.py
'''

    # Import packages
import numpy as np
import pandas as pd
import blimpy as bl
import os
import math
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
plt.rcParams.update({'font.size': 22})
plt.rcParams['axes.formatter.useoffset'] = False

# Check if $DISPLAY is set (for handling plotting on remote machines with no X-forwarding)

if 'DISPLAY' in os.environ.keys():
    import pylab as plt
else:
    matplotlib.use('Agg')
    import pylab as plt

MAX_PLT_POINTS      = 65536                  # Max number of points in matplotlib plot
MAX_IMSHOW_POINTS   = (8192, 4096)           # Max number of points in imshow plot

    # Define Functions
def db(x, offset=0):
    """ Convert linear to dB """
    return 10 * np.log10(x + offset)

def normalize(x,xmin=None,xmax=None):
    if xmin==None:
        xmin=x.min()
    if xmax==None:
        xmax=x.max()
    return (x-xmin)/(xmax-xmin)

def rebin(d, n_x=None, n_y=None, n_z=None):
    """ Rebin data by averaging bins together
    Args:
    d (np.array): data
    n_x (int): number of bins in x dir to rebin into one
    n_y (int): number of bins in y dir to rebin into one
    Returns:
    d: rebinned data with shape (n_x, n_y)
    """
    if n_x is None:
        n_x = 1
    else:
        n_x = math.ceil(n_x)
    if n_y is None:
        n_y = 1
    else:
        n_y = math.ceil(n_y)
    if n_z is None:
        n_z = 1
    else:
        n_z = math.ceil(n_z)
    if d.ndim == 3:
        d = d[:int(d.shape[0] // n_x) * n_x, :int(d.shape[1] // n_y) * n_y, :int(d.shape[2] // n_z) * n_z]
        d = d.reshape((d.shape[0] // n_x, n_x, d.shape[1] // n_y, n_y, d.shape[2] // n_z, n_z))
        d = d.mean(axis=5)
        d = d.mean(axis=3)
        d = d.mean(axis=1)
    elif d.ndim == 2:
        d = d[:int(d.shape[0] // n_x) * n_x, :int(d.shape[1] // n_y) * n_y]
        d = d.reshape((d.shape[0] // n_x, n_x, d.shape[1] // n_y, n_y))
        d = d.mean(axis=3)
        d = d.mean(axis=1)
    elif d.ndim == 1:
        d = d[:int(d.shape[0] // n_x) * n_x]
        d = d.reshape((d.shape[0] // n_x, n_x))
        d = d.mean(axis=1)
    else:
        raise RuntimeError("Only NDIM <= 3 supported")
    return d

def calc_extent(plot_f=None, plot_t=None, MJD_time=False):
    """ Setup plotting edges.
    """
    plot_f_begin = plot_f[0]
    plot_f_end = plot_f[-1] + (plot_f[1] - plot_f[0])
    span = np.abs(plot_f_begin - plot_f_end)
    if span > 1:
        factor=1
    elif span*10**3>1:
        factor=10**3
    elif span*10**6>1:
        factor=10**6
    else:
        factor=10**9
    plot_f_begin = span/2*factor
    plot_f_end = span/-2*factor
    plot_t_begin = plot_t[0]
    plot_t_end = plot_t[-1] + (plot_t[1] - plot_t[0])
    if MJD_time:
        extent = (plot_f_begin, plot_f_end, plot_t_begin, plot_t_end)
    else:
        extent = (plot_f_begin, plot_f_end, 0.0, (plot_t_end - plot_t_begin) * 24. * 60. * 60)
    return extent

# subplotting workhorse function. Actually gets the data and adds it to the subplots.
def plot_waterfall_subplots(wf, index, ax, fig, f_start=None, f_stop=None, xmin=None, xmax=None, 
                            if_id=0, logged=True, cb=True, MJD_time=False, **kwargs):
    plot_f, plot_data = wf.grab_data(min(f_start, f_stop),max(f_start, f_stop), if_id)
    # imshow does not support int8, so convert to floating point
    plot_data = plot_data.astype('float32')
    # plot the power in logspace unless the data is weird and has zeroes or negatives
    if logged:
        if not plot_data.all()<=0.0:
            plot_data = db(plot_data)
    # Make sure waterfall plot is under 4k*4k
    dec_fac_x, dec_fac_y = 1, 1
    if plot_data.shape[0] > MAX_IMSHOW_POINTS[0]:
        dec_fac_x = int(plot_data.shape[0] / MAX_IMSHOW_POINTS[0])
    if plot_data.shape[1] > MAX_IMSHOW_POINTS[1]:
        dec_fac_y = int(plot_data.shape[1] / MAX_IMSHOW_POINTS[1])
    plot_data = rebin(plot_data, dec_fac_x, dec_fac_y)
    # normalize the power to the range of the target beam
    if index==0:
        xmin=plot_data.min()
        xmax=plot_data.max()
    plot_data = normalize(plot_data,xmin,xmax)
    # calculate the plot extent/axes 
    extent = calc_extent(plot_f=plot_f, plot_t=wf.timestamps, MJD_time=MJD_time)
    im = ax[index].imshow(plot_data,
               aspect='auto',
               origin='lower',
               rasterized=True,
               interpolation='nearest',
               extent=extent,
               cmap='viridis',
               vmin=0, 
               vmax=1,
               **kwargs)
    # add colorbar
    if cb:
        fig.colorbar(im, ax=ax[index])
    # get the x-axis label right for the frequency scale
    if np.abs(plot_f[0]-plot_f[-1]) > 1:   
        label = 'MHz'
    elif np.abs(plot_f[0]-plot_f[-1])*10**3 > 1:
        label = 'kHz'
    elif np.abs(plot_f[0]-plot_f[-1])*10**6 > 1:
        label = 'Hz'
    else:
        label = 'GHz?'
    freq_mid = (plot_f[1]+plot_f[-1])/2    
    ax[index].set_xlabel(f"Frequency [{label}]\nCentered at {freq_mid:.6f} MHz")
    ax[index].tick_params(axis='x', which='major', labelsize=22)
    ax[index].tick_params(axis='x', which='minor', labelsize=14)
    # set the y-axis label
    if MJD_time:
        ax[index].set_ylabel("Time [MJD]")
    else:
        ax[index].set_ylabel("Time [s]")
    return xmin,xmax

# makes both the title of the plot and the filename
def make_title(fig,MJD,f2,fmid,drift_rate,SNR,corrs,SNRr,x):
    title=f'MJD: {MJD} || fmax: {f2:.6f} MHz'
    filename=f"MJD_{MJD}_fmid{fmid:.6f}"
    if drift_rate:
        title+=f' || Drift Rate: {drift_rate:.3f} Hz/s ({drift_rate/f2*1000:.3f} nHz)'
        filename+=f"_DR{drift_rate:.3f}"
    if SNR:
        title+=f' || SNR: {SNR:.3f}\n'
    if corrs:
        title+=f'Correlation Score: {corrs:.3f}'
        filename+=f"_x{corrs:.3f}"
    if SNRr:
        title+=f' || SNR ratio: {SNRr:.3f}'
        filename+=f"_SNRr{SNRr:.3f}"
    if x:
        title+=f' || X score: {x:.3f}'
        filename+=f"_X_{x:.3f}"
    fig.suptitle(title,size=25)
    fig.tight_layout(rect=[0, 0, 1, 1.05])
    return filename

# first plotting function that sets up the plot, sends info to the subplotter, gets the title and saves the plot.
def plot_beams(name_array, fstart, fstop, drift_rate=None, SNR=None, corrs=None, SNRr=None, x=None, path='./', pdf=False):
    # make waterfall objects for plotting from the filenames
    fil_array = []
    f1 = min(fstart,fstop)
    f2 = max(fstart,fstop)
    fmid=round((f2+f1)/2,6)
    for beam in name_array:
        test_wat = bl.Waterfall(beam, 
                            f_start=f1, 
                            f_stop=f2)
        fil_array.append(test_wat)
    # initialize the plot
    nsubplots = len(name_array)
    nrows = int(np.floor(np.sqrt(nsubplots)))
    ncols = int(np.ceil(nsubplots/nrows))
    fig, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=(20,7))
    # call the plotting function and plot the waterfall objects in fil_array
    i=0
    xmin=None
    xmax=None
    for r in range(nrows):
        for c in range(ncols):
            fil = fil_array[i]
            xmin,xmax=plot_waterfall_subplots(fil, 
                                    i, ax, fig, 
                                    f_start=f1, 
                                    f_stop=f2,
                                    xmin=xmin,
                                    xmax=xmax)
            # set subplot titles
            if SNR and SNRr:
                if i==0:
                    ax[i].set_title(f"target beam || SNR: {SNR:.3f}")
                else:
                    ax[i].set_title(f"off beam || SNR*: {SNR/SNRr:.3f}")
            else:
                ax[i].set_title([f"target beam" if index==0 else "off beam"][0])
            i+=1
    # set the overall plot title and filename
    name_deconstructed = fil.filename.split('/')[-1].split('_')
    MJD = name_deconstructed[1] + '_' + name_deconstructed[2] #+ '_' + name_deconstructed[3]
    filename=make_title(fig,MJD,f2,fmid,drift_rate,SNR,corrs,SNRr,x)
    # save the plot
    if pdf==True:
        ext='pdf'
    else:
        ext='png'
    plt.savefig(f'{path}{filename}.{ext}',
                bbox_inches='tight',format=ext,dpi=fig.dpi,facecolor='white', transparent=False)
    plt.close()
    return None

# initial function to set up plotting by manually input frequencies
def plot_by_freqs(df0,freqs,path,pdf):
    df = df0.drop_duplicates(subset="dat_name", keep="first")
    for index, row in df.reset_index(drop=True).iterrows():
        beams = [row[i] for i in list(df) if i.startswith('fil_')]
        if check_freqs(beams[0],freqs)=='out_of_bounds':
            print(f"Input frequencies {freqs} not within the frequency span of the data in\n{beams[0]}\nSkipping this file.")
            continue
        fstart=max(freqs)
        fend=min(freqs)
        print(f'Plotting {index+1}/{len(df)} from {fend:.6f} MHz to {fstart:.6f} MHz\n{row["dat_name"]}\n')
        plot_beams(beams,fstart,fend,path=path,pdf=pdf)
    return len(df)

# used in plot_by_freqs() to check if the frequencies are within 
# the bounds of the filterbank file 
def check_freqs(fil,freqs):
    fil_meta = bl.Waterfall(target_fil,load_data=False)
    minimum_frequency = fil_meta.container.f_start
    maximum_frequency = fil_meta.container.f_stop
    for freq in freqs:
        if freq>maximum_frequency or freq<minimum_frequency:
            return 'out_of_bounds'
    return 'within_bounds'


# plots the histograms showing snr, frequency, and drift rates of all the hits
# mainly just used at the end of DOTnbeam or DOTparallel
def diagnostic_plotter(df, tag, saving=False, log=True, outdir='./'):
    # initialize figure with subplots
    fig, ax = plt.subplots(nrows=1, ncols=3, figsize=((20,5)))
    label_size=20
    tick_label_size=14
    tick_size=4
    w=2
    # snr histogram subplot
    s=0
    ax[s].semilogy()
    ax[s].tick_params(axis='both', which='major', size=tick_size, labelsize=tick_label_size, width=w)
    ax[s].set_xlabel('SNR',size=label_size)
    ax[s].set_ylabel('Count',size=label_size)
    ax[s].set_title('SNR Distribution',size=label_size)
    ax[s].hist(df['SNR'], 
         bins=100,
         range=[0,1000],
        color='rebeccapurple');
    # freq histogram subplot
    s=1
    if log == True:
        ax[s].semilogy()
    ax[s].tick_params(axis='both', which='major', size=tick_size, labelsize=tick_label_size, width=w)
    ax[s].set_xlabel('Frequency (GHz)',size=label_size)
    ax[s].set_ylabel('Count',size=label_size)
    ax[s].set_title('Frequency Distribution',size=label_size)
    ax[s].hist(df['Corrected_Frequency'], 
        bins=100,
        color='teal');
    # drift rate histogram subplot
    s=2
    ax[s].semilogy()
    ax[s].tick_params(axis='both', which='major', size=tick_size, labelsize=tick_label_size, width=w)
    ax[s].set_xlabel('Drift Rate (nHz)',size=label_size)
    ax[s].set_ylabel('Count',size=label_size)
    ax[s].set_title('Drift Rate Distribution',size=label_size)
    ax[s].hist(df['normalized_dr'], 
         bins=100,
        color='firebrick');
    # adjust layout and save figure
    fig.text(0.5, 0.98, tag.replace('sfh','spatially_filtered_hits').replace('_',' '), va='top', ha='center', size=26)
    fig.tight_layout(rect=[0, 0, 1, 0.9])
    if saving == True:
        plt.savefig(outdir + tag + '_diagnostic_plots.jpg')
        plt.close()
    else:
        plt.show()
    return None