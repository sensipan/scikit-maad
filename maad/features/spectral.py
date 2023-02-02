#!/usr/bin/env python
"""
Collection of functions to extract spectral features from audio signals
"""
#
# Authors:  Juan Sebastian ULLOA <lisofomia@gmail.com>
#           Sylvain HAUPERT <sylvain.haupert@mnhn.fr>
#
# License: New BSD License

# =============================================================================
# Load the modules
# =============================================================================
# Import external modules
import numpy as np
import pandas as pd
from scipy import interpolate
from numpy.lib.function_base import _quantile_is_valid

# Import internal modules
from maad.util import moments, power2dB
from maad import sound

#%%
# =============================================================================
# public functions
# =============================================================================
#%%
def spectral_moments (X, axis=None):
    """
    Computes the first 4th moments of an amplitude spectrum (1d) or spectrogram (2d),
    mean, variance, skewness, kurtosis.

    Parameters
    ----------
    X : ndarray of floats
        Amplitude  spectrum (1d) or spectrogram (2d).
    axis : interger, optional, default is None
        if spectrogram (2d), select the axis to estimate the moments.

    Returns
    -------
    mean : float
        mean of the audio
    var : float
        variance  of the audio
    skew : float
        skewness of the audio
    kurt : float
        kurtosis of the audio

    Examples
    --------
    >>> from maad import sound
    >>> s, fs = sound.load('../data/spinetail.wav')
    >>> Sxx_power,_,_,_ = sound.spectrogram (s, fs)

    Compute spectral moments on the mean spectrum

    >>> import numpy as np
    >>> S_power = sound.avg_power_spectro(Sxx_power)
    >>> sm, sv, ss, sk = features.spectral_moments (S_power)
    >>> print('mean: %2.8f / var: %2.10f / skewness: %2.2f / kurtosis: %2.2f' % (sm, sv, ss, sk))
    mean: 0.00000228 / var: 0.0000000001 / skewness: 5.84 / kurtosis: 40.49

    Compute spectral moments of the spectrogram along the time axis

    >>> from maad.features import spectral_moments
    >>> sm_per_bin, sv_per_bin, ss_per_bin, sk_per_bin = spectral_moments(Sxx_power, axis=1)
    >>> print('Length of sk_per_bin is : %2.0f' % len(sk_per_bin))
    Length of sk is : 512

    """
    # force P to be ndarray
    X = np.asarray(X)

    return moments(X,axis)

#%%
def peak_frequency(s, fs, method='best', nperseg=1024, roi=None, amp=False, as_pandas=False, **kwargs):
    """
    Compute the peak frequency for audio signal. The peak frequency is the frequency of
    maximum power. If a region of interest with time and spectral limits is provided,
    the peak frequency is computed on the selection.

    Parameters
    ----------
    s : 1D array
        Input audio signal
    fs : float
        Sampling frequency of audio signal
    method : {'fast', 'best'}, optional
        Method used to compute the peak frequency.
        The default is 'best'.
    nperseg : int, optional
        Length of segment to compute the FFT. The default is 1024.
    roi : pandas.Series, optional
        Region of interest where peak frequency will be computed.
        Series must have a valid input format with index: min_t, min_f, max_t, max_f.
        The default is None.
    as_pandas: bool
        Return data as a pandas.Series or pandas.DataFrame, when amp
        is False or True, respectively. Default is False.
    kwargs : additional keyword arguments
        If `window='hann'`, additional keyword arguments to pass to
        `sound.spectrum`.

    Returns
    -------
    peak_freq : float
        Peak frequency of audio segment.
    amp_peak_freq : float
        Amplitud of the peak frequency of audio segment.

    Examples
    --------
    >>> from maad import features, sound
    >>> s, fs = sound.load('../../data/spinetail.wav')

    Compute peak frequency with the fast method

    >>> peak_freq, peak_freq_amp = features.peak_frequency(s, fs)
    >>> print('Peak Frequency: {:.5f}, Amplitud: {:.5f}'.format(peak_freq, peak_freq_amp))
    Peak Frequency: 6634.16016, Amplitud: 0.00013

    """
    if roi is None:
        pxx, fidx = sound.spectrum(s, fs, nperseg, **kwargs)
    else:
        pxx, fidx = sound.spectrum(s, fs, nperseg,
                                   tlims=[roi.min_t, roi.max_t],
                                   flims=[roi.min_f, roi.max_f],
                                   **kwargs)
    pxx = pd.Series(pxx, index=fidx)

    # simplest form to get peak frequency, but less precise
    if method=='fast':
        peak_freq = pxx.idxmax()
        amp_peak_freq = pxx[peak_freq]

    elif method=='best':
        # use interpolation get more precise peak frequency estimation
        idxmax = pxx.index.get_loc(pxx.idxmax())
        x = pxx.iloc[[idxmax-1, idxmax, idxmax+1]].index.values
        y = pxx.iloc[[idxmax-1, idxmax, idxmax+1]].values
        f = interpolate.interp1d(x,y, kind='quadratic')
        xnew = np.arange(x[0], x[2], 1)
        ynew = f(xnew)
        peak_freq = xnew[ynew.argmax()]
        amp_peak_freq = ynew[ynew.argmax()]

    else:
        raise Exception("Invalid method. Method should be 'fast' or 'best' ")

    if amp:
        if as_pandas:
            out = pd.DataFrame({"freq":peak_freq, "amp":amp_peak_freq}, index=[0])
        else:
            out = np.array([peak_freq, amp_peak_freq])
    else:
        if as_pandas:
            out = pd.Series([peak_freq], index=["peak_freq"])
        else:
            out = peak_freq

    
    return out

#%%
def spectral_quantile(s, fs, q=[0.05, 0.25, 0.5, 0.75, 0.95], nperseg=1024, roi=None,
                      as_pandas=False, amp=False, **kwargs):
    """
    Compute the q-th quantile of the power spectrum. If a region of interest with time and
    spectral limits is provided, the q-th quantile is computed on the selection.

    Parameters
    ----------
    s : 1D array
        Input audio signal
    fs : float
        Sampling frequency of audio signal
    q : array or float, optional
        Quantile or sequence of quantiles to compute, which must be between 0 and 1
        inclusive.
        The defaul is [0.05, 0.25, 0.5, 0.75, 0.95].
    nperseg : int, optional
        Length of segment to compute the FFT. The default is 1024.
    roi : pandas.Series, optional
        Region of interest where peak frequency will be computed.
        Series must have a valid input format with index: min_t, min_f, max_t, max_f.
        The default is None.
    as_pandas: bool
        Return data as a pandas.Series or pandas.DataFrame, when amp
        is False or True, respectively. Default is False.
    amp: bool
        Enable quantiles amplitude output. Default is False.
    kwargs : additional keyword arguments
        If `window='hann'`, additional keyword arguments to pass to
        `sound.spectrum`.
    Returns
    -------
    Pandas Series or Numpy array
        Quantiles of power spectrum.

    Examples
    --------
    >>> from maad import sound, features
    >>> s, fs = sound.load('../../data/spinetail.wav')

    Compute the q-th quantile of the power spectrum

    >>> qs = features.spectral_quantile(s, fs, [0.05, 0.25, 0.5, 0.75, 0.95])
    >>> print("5%: {:.2f} / 25%: {:.2f} / 50%: {:.2f} / 75%: {:.2f} \
    >>> / 95%: {:.2f}".format(qs[0], qs[1], qs[2], qs[3], qs[4]))
    5%: 6029.30 / 25%: 6416.89 / 50%: 6632.23 / 75%: 6890.62 / 95%: 9216.21

    """
    q = np.asanyarray(q)
    if not _quantile_is_valid(q):
        raise ValueError("Percentiles must be in the range [0, 100]")

    # Compute spectrum
    if roi is None:
        pxx, fidx = sound.spectrum(s, fs, nperseg, **kwargs)
    else:
        pxx, fidx = sound.spectrum(s, fs, nperseg,
                                   tlims=[roi.min_t, roi.max_t],
                                   flims=[roi.min_f, roi.max_f],
                                   **kwargs)
    pxx = pd.Series(pxx, index=fidx)

    # Compute spectral q
    norm_cumsum = pxx.cumsum()/pxx.sum()
    spec_quantile = []
    for quantile in q:
        spec_quantile.append(pxx.index[np.where(norm_cumsum>=quantile)[0][0]])

    if amp:
        if as_pandas:
            out = pd.DataFrame({"freq":spec_quantile, "amp":pxx[spec_quantile].values}, index=q)
        else:
            out = np.transpose(np.matrix([q, spec_quantile, pxx[spec_quantile]]))
    else:
        if as_pandas:
            out = pd.Series(spec_quantile, index=q)
        else:
            out = np.array(spec_quantile)

    return out

#%%
def spectral_quantile1(s, fs, q=[0.05, 0.25, 0.5, 0.75, 0.95], nperseg=1024, roi=None,
                      as_pandas=False, amp=False, **kwargs):
    """
    Compute the q-th quantile of the power spectrum. If a region of interest with time and
    spectral limits is provided, the q-th quantile is computed on the selection.

    """
    q = np.asanyarray(q)
    if not _quantile_is_valid(q):
        raise ValueError("Percentiles must be in the range [0, 100]")

    # Compute spectrum
    if roi is None:
        Sxx,tn,_,_ = sound.spectrogram(s, fs, nperseg=nperseg, **kwargs)
    else:
        Sxx,tn,_,_ = sound.spectrogram(s, fs, nperseg=nperseg, 
                                      tlims=[roi.min_t, roi.max_t], flims=[roi.min_f, roi.max_f],
                                      **kwargs)
    Sxx = pd.Series(np.average(Sxx,axis=0), index=tn)

    # Compute spectral q
    norm_cumsum = Sxx.cumsum()/Sxx.sum()
    spec_quantile = []
    for quantile in q:
        spec_quantile.append(Sxx.index[np.where(norm_cumsum>=quantile)[0][0]])

    if amp:
        if as_pandas:
            out = pd.DataFrame({"time":spec_quantile, "amp":Sxx[spec_quantile].values}, index=q)
        else:
            out = np.transpose(np.matrix([q, spec_quantile, Sxx[spec_quantile]]))
    else:
        if as_pandas:
            out = pd.Series(spec_quantile, index=q)
        else:
            out = np.array(spec_quantile)

    return out


#%%
def bandwidth(s, fs, nperseg=1024, roi=None,  mode="quantile", method='fast',
              threshold=1.0, reference="peak", dB=3, as_pandas=False,  **kwargs):
    """
    Compute the bandwith of the power spectrum. If a region of interest with time
    and spectral limits is provided, the bandwidth is computed on the selection.

    Parameters
    ----------
    s : 1D array
        Input audio signal
    fs : float
        Sampling frequency of audio signal
    nperseg : int, optional
        Length of segment to compute the FFT. The default is 1024.
    roi : pandas.Series, optional
        Region of interest where peak frequency will be computed.
        Series must have a valid input format with index: min_t, min_f, max_t, max_f.
        The default is None.
    mode : {'quantile', '3dB'}, optional
        Method used to compute the spectral bandwidth.
        The default is 'quantile'.
    method : {'fast', 'best'}, optional
        Method used to compute the peak frequency.
        The default is 'fast'.
    threshold : float
        Threshold to caculate the bandwith from the reference frequency.
        Default is 0.5.
    reference : {'peak', 'central'}, optional
        Reference point to calculate the bandwith.
        Default is "peak"
    dB: float, optional
        The X dB bandwidth, the frequency at which the signal amplitude
        reduces by x dB (when x= 3 the frequency becomes half its value).
        Default is -3.
    as_pandas_series: bool
        Return data as a pandas.Series. This is usefull when computing multiple features
        over a signal. Default is False.
    kwargs : additional keyword arguments
        If `window='hann'`, additional keyword arguments to pass to
        `sound.spectrum`.
    Returns
    -------
    bandwidth : float
        Bandwidth 50% of the audio
    bandwidth_90 : float
        Bandwidth 90%  of the audio
    bandwidth_xdB : float
        XdB_Bandwidth of the audio
    Examples
    --------
    >>> from maad import features, sound
    >>> s, fs = sound.load('../../data/spinetail.wav')

    Compute the bandwidth of the power spectrum using quantiles

    >>> bw, bw_90 = features.bandwidth(s, fs, mode="quantile", as_pandas=True)
    >>> print("Bandwidth: {:.4f} / Bandwidth 90% {:.4f}".format(bw, bw_90))
    Bandwidth: 473.7305 / Bandwidth 90% 3186.9141

    Compute the 3 dB bandwidth of the power spectrum using the peak frequency as reference

    >>> dB3_bw = features.bandwidth(s, fs, mode="3dB", reference="peak")
    >>> print("3dB bandwidth : {:.4f} ".format(dB3_bw))
    3dB bandwidth : 344.5312

    """
    # Compute spectral bandwith with the quantiles
    if mode=="quantile":
        q = spectral_quantile(s, fs, [0.05, 0.25, 0.75, 0.95], 
                              nperseg, roi, as_pandas, False, **kwargs)
        # Compute spectral bandwidth
        if as_pandas:
            out = pd.Series([np.abs(q.iloc[2]-q.iloc[1]), np.abs(q.iloc[3]-q.iloc[0])],
                              index=["bandwidth_50", "bandwidth_90"])
        else:
            out = np.array([np.abs(q[2]-q[1]), np.abs(q[3]-q[0])])

        return out
    # Compute spectral X-bB Bandwidth
    if mode=="3dB":
        #intersect_points = pulse_rate(s, fs, nperseg, roi, dB, method,
        #                              threshold, reference, False, **kwargs)
        if roi is None:
            Sxx_power,_,fn,_ = sound.spectrogram(s, fs, nperseg=nperseg, mode='psd', **kwargs)
        else:
            Sxx_power,_,fn,_ = sound.spectrogram(s, fs, nperseg=nperseg, mode='psd',
                                                tlims=[roi.min_t, roi.max_t],
                                                flims=[roi.min_f, roi.max_f],
                                                **kwargs)
        # peak_freq, amp_peak_freq = peak_frequency(s, fs, method, nperseg, roi, False, dB, method)
        # spec, f_idx = sound.spectrum(s, fs, nperseg, method="periodogram", **kwargs)
        # Sxx_power,tn,fn,_ = sound.spectrogram (s, fs, nperseg=nperseg, mode='psd', **kwargs)
        # matlab or raven
        S_power_mean = np.mean(Sxx_power, axis=1)
        Sxx_dB = pd.Series(power2dB(S_power_mean), index=fn)

        # compute peak frequency and its amplitud in dB
        if reference=="peak":
            #peak_freq, amp_peak_freq = features.peak_frequency(s, fs), method, nperseg, roi, False)
            #amp_peak_freq = power2dB(amp_peak_freq, db_range, db_gain)
            peak_freq = Sxx_dB.idxmax()
            amp_peak_freq = Sxx_dB[peak_freq]
            threshold_array = (amp_peak_freq-dB)*np.ones_like(Sxx_dB)
        # compute central frequency and its amplitud in dB
        elif reference=="central":
            central_freq_matrix = spectral_quantile(s, fs, [0.5], nperseg, roi, False, True)
            _, central_freq_amp = central_freq_matrix[0,0], central_freq_matrix[0,1]
            central_freq_amp = power2dB(central_freq_amp)
            threshold_array = (central_freq_amp-dB)*np.ones_like(Sxx_dB)
        else:
            raise Exception("Invalid reference. Reference should be 'central' or 'peak'")
        if method=='best': # interpolation
            pass
        elif method=='fast': # pandas indexation
            intersect_points = np.where(np.abs(Sxx_dB-threshold_array)<threshold)[0]
            candidates = np.split(intersect_points, np.where(np.diff(intersect_points) != 1)[0]+1)
            intersect_points = []
            for cand in candidates:
                dif = np.abs(Sxx_dB[fn[cand]].values-threshold).argmin()
                intersect_points.append(fn[cand[dif]])

            if len(intersect_points)==2:
                bw_3dB = intersect_points[1]-intersect_points[0]
            else:
                bw_3dB = intersect_points[-1]-intersect_points[0]

            if as_pandas:
                out = pd.Series(bw_3dB, index=["bandwidth_3dB"])
            else:
                out = bw_3dB
            return out
        else:
            raise Exception("Invalid method. Method should be 'best' or 'fast'")
    else:
        raise Exception("Invalid mode. Mode should be 'quantile' or '3dB'")


#%% ---------------
# # Frequencia
# # - peak frequency      ok
# # - spectrum quantile   ok
# # - Bandwidth           ok (3dB missing method fast without interpolation)
# # - max freq            ok
# # - min freq            ok
# # Tiempo
# # - quantile                 ok
# # - Center time              ok
# # - Duration                 ok
# # notebook with examples and comparison with raven
# # - Call rate / Pulse Rate     https://www.avisoft.com/tutorials/measuring-sound-parameters-from-the-spectrogram-automatically/
#    env vs time NOT dB vs freq. scipy.signal.find_peaks
#    **check python compatibility**
# # Spectro-temporal            timeR seewave
# # - pitch tracking veremos!   
# pip install pylint

# info, sox
# load

# minimal frequency is not working
# peak frequency amp
# as_pandas_series -> as_pandas
# 3dB - improve
# temporal quantile errors, why? (Nt), probar desde el espectrograma (look it)
# big window to detect, audio signal segementation algorithms (signal processing)
# 