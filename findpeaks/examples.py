# %%
# import os
# os.chdir(os.path.dirname(os.path.abspath('examples.py')))
import findpeaks
print(dir(findpeaks))
print(findpeaks.__version__)

# %% Denoising example
from findpeaks import findpeaks
fp = findpeaks()
img = fp.import_example('2dpeaks_image')
import findpeaks

    
# filters parameters
# window size
winsize = 9
# damping factor for frost
k_value1 = 2.0
# damping factor for lee enhanced
k_value2 = 1.0
# coefficient of variation of noise
cu_value = 0.25
# coefficient of variation for lee enhanced of noise
cu_lee_enhanced = 0.523
# max coefficient of variation for lee enhanced
cmax_value = 1.73

# Some pre-processing
# Resize
img = findpeaks.stats.resize(img, size=(300,300))
# Make grey image
img = findpeaks.stats.togray(img)
# Scale between [0-255]
img = findpeaks.stats.scale(img)

# Denoising
# fastnl
img_fastnl = findpeaks.stats.denoise(img, method='fastnl', window=winsize)
# bilateral
img_bilateral = findpeaks.stats.denoise(img, method='bilateral', window=winsize)
# frost filter
image_frost = findpeaks.frost_filter(img, damping_factor=k_value1, win_size=winsize)
# kuan filter
image_kuan = findpeaks.kuan_filter(img, win_size=winsize, cu=cu_value)
# lee filter
image_lee = findpeaks.lee_filter(img, win_size=winsize, cu=cu_value)
# lee enhanced filter
image_lee_enhanced = findpeaks.lee_enhanced_filter(img, win_size=winsize, k=k_value2, cu=cu_lee_enhanced, cmax=cmax_value)
# mean filter
image_mean = findpeaks.mean_filter(img, win_size=winsize)
# median filter
image_median = findpeaks.median_filter(img, win_size=winsize)

# Plotting
import matplotlib.pyplot as plt
fig, ax =  plt.subplots(1,8, figsize=(8,20))
ax[0].imshow(img_fastnl)
ax[1].imshow(img_bilateral)
ax[2].imshow(image_frost)
ax[3].imshow(image_kuan)
ax[4].imshow(image_lee)
ax[5].imshow(image_lee_enhanced)
ax[6].imshow(image_mean)
ax[7].imshow(image_median)

# %% Run over all methods and many parameters
from findpeaks import findpeaks
savepath='./comparison_methods/'
filters = ['fastnl','bilateral','frost','median','mean', None]
windows = [3, 9, 15, 31, 63]
cus = [0.25, 0.5, 0.75]

for getfilter in filters:
    for window in windows:
            fp = findpeaks(mask=0, scale=True, denoise=getfilter, window=window, togray=True, resize=(300,300), verbose=3)
            img = fp.import_example('2dpeaks_image')
            results = fp.fit(img)
            title = 'Method=' + str(getfilter) + ', window='+str(window)
            _, ax1 = fp.plot_mesh(wireframe=False, title=title, savepath=savepath+title+'.png')

filters = ['lee','lee_enhanced','kuan']
for getfilter in filters:
    for window in windows:
        for cu in cus:
            fp = findpeaks(mask=0, scale=True, denoise=getfilter, window=window, cu=cu, togray=True, resize=(300,300), verbose=3)
            img = fp.import_example('2dpeaks_image')
            results = fp.fit(img)
            title = 'Method=' + str(getfilter) + ', window='+str(window) + ', cu='+str(cu)
            _, ax1 = fp.plot_mesh(wireframe=False, title=title, savepath=savepath+title+'.png')


#%% Plot each seperately
fp.plot_preprocessing()
fp.plot_mask()
fp.plot_peristence()
fp.plot_mesh()

# Make mesh plot
fp.plot_mesh(view=(0,90))
fp.plot_mesh(view=(90,0))


# %%
from findpeaks import findpeaks
fp = findpeaks()
X = fp.import_example('1dpeaks')

fp = findpeaks(lookahead=1, interpolate=10, verbose=3)
fp.fit(X[:,1])
fp.plot()
fp.plot_peristence()


# %%
from findpeaks import findpeaks
img = fp.import_example()

# 2dpeaks example
fp = findpeaks()
fp.fit(img)
fp.plot()

# 2dpeaks example with other settings
fp = findpeaks(mask=0, scale=True, denoise=10, togray=True, resize=(300,300), verbose=3)
img = fp.import_example('2dpeaks')
fp.fit(img)
fp.plot()

# %%
from findpeaks import findpeaks
fp = findpeaks(mask=0)
X = fp.import_example()
fp.fit(X)
fp.plot()

fp.plot_preprocessing()
fp.plot_mask()
fp.plot_mesh()
fp.plot_peristence()

# %%
from findpeaks import findpeaks
X = [1,1,1.1,1,0.9,1,1,1.1,1,0.9,1,1.1,1,1,0.9,1,1,1.1,1,1,1,1,1.1,0.9,1,1.1,1,1,0.9,1,1.1,1,1,1.1,1,0.8,0.9,1,1.2,0.9,1,1,1.1,1.2,1,1.5,1,3,2,5,3,2,1,1,1,0.9,1,1,3,2.6,4,3,3.2,2,1,1,0.8,4,4,2,2.5,1,1,1]

fp = findpeaks(lookahead=1, verbose=3)
fp.fit(X)
fp.plot()
fp.plot_peristence()

fp = findpeaks(lookahead=1, interpolate=10, verbose=3)
fp.fit(X)
fp.plot()

# %%
X = [10,11,9,23,21,11,45,20,11,12]
fp = findpeaks(lookahead=1, interpolate=10)
fp.fit(X)
fp.plot()

# %%
from math import pi
import numpy as np

i = 10000
xs = np.linspace(0,3.7*pi,i)
X = (0.3*np.sin(xs) + np.sin(1.3 * xs) + 0.9 * np.sin(4.2 * xs) + 0.06 * np.random.randn(i))

# Findpeaks
fp = findpeaks()
results=fp.fit(X)
fp.plot()

results['max_peaks_s']
results['min_peaks_s']
results['labx_s']
