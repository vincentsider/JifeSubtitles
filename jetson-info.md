# Jetson System Information
**Generated:** Tue Dec 23 07:46:26 PM CET 2025

## L4T Version
```
# R36 (release), REVISION: 4.4, GCID: 41062509, BOARD: generic, EABI: aarch64, DATE: Mon Jun 16 16:07:13 UTC 2025
# KERNEL_VARIANT: oot
TARGET_USERSPACE_LIB_DIR=nvidia
TARGET_USERSPACE_LIB_DIR_PATH=usr/lib/aarch64-linux-gnu/nvidia
```

## JetPack Version
```
Package: nvidia-jetpack
Version: 6.2.1+b38
Description: NVIDIA Jetpack Meta Package
Package: nvidia-jetpack
Version: 6.2+b77
Description: NVIDIA Jetpack Meta Package
Package: nvidia-jetpack
Version: 6.1+b123
Description: NVIDIA Jetpack Meta Package
```

## Hardware Model
```
NVIDIA Jetson Orin NX Engineering Reference Developer Kit
```

## Power Mode
```
NV Power Mode: MAXN_SUPER
2
```

## CUDA Version
```

```

## GPU/CPU Clocks
```
SOC family:tegra234  Machine:NVIDIA Jetson Orin NX Engineering Reference Developer Kit
Online CPUs: 0-5
cpu0:  Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=1510400 IdleStates: WFI=1 c7=1 
cpu1:  Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=1497600 IdleStates: WFI=1 c7=1 
cpu2:  Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=1190400 IdleStates: WFI=1 c7=1 
cpu3:  Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=1113600 IdleStates: WFI=1 c7=1 
cpu4:  Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=729600 IdleStates: WFI=1 c7=1 
cpu5:  Online=1 Governor=schedutil MinFreq=729600 MaxFreq=1510400 CurrentFreq=883200 IdleStates: WFI=1 c7=1 
GPU MinFreq=306000000 MaxFreq=624750000 CurrentFreq=306000000
Active GPU TPCs: 2
EMC MinFreq=204000000 MaxFreq=2133000000 CurrentFreq=2133000000 FreqOverride=0
FAN Dynamic Speed Control=nvfancontrol hwmon0_pwm1=65
NV Power Mode: MAXN_SUPER
```

## Memory
```
               total        used        free      shared  buff/cache   available
Mem:           7.4Gi       5.7Gi       600Mi        29Mi       1.2Gi       1.5Gi
Swap:          3.7Gi       1.3Gi       2.4Gi
```

## Disk Space
```
Filesystem       Size  Used Avail Use% Mounted on
/dev/nvme0n1p1   233G   15G  206G   7% /
/dev/nvme0n1p10   63M  110K   63M   1% /boot/efi
```

## Audio Devices
```
**** List of CAPTURE Hardware Devices ****
card 1: APE [NVIDIA Jetson Orin NX APE], device 0: tegra-dlink-0 XBAR-ADMAIF1-0 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 1: tegra-dlink-1 XBAR-ADMAIF2-1 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 2: tegra-dlink-2 XBAR-ADMAIF3-2 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 3: tegra-dlink-3 XBAR-ADMAIF4-3 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 4: tegra-dlink-4 XBAR-ADMAIF5-4 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 5: tegra-dlink-5 XBAR-ADMAIF6-5 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 6: tegra-dlink-6 XBAR-ADMAIF7-6 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 7: tegra-dlink-7 XBAR-ADMAIF8-7 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 8: tegra-dlink-8 XBAR-ADMAIF9-8 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 9: tegra-dlink-9 XBAR-ADMAIF10-9 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 10: tegra-dlink-10 XBAR-ADMAIF11-10 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 11: tegra-dlink-11 XBAR-ADMAIF12-11 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 12: tegra-dlink-12 XBAR-ADMAIF13-12 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 13: tegra-dlink-13 XBAR-ADMAIF14-13 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 14: tegra-dlink-14 XBAR-ADMAIF15-14 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 15: tegra-dlink-15 XBAR-ADMAIF16-15 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 16: tegra-dlink-16 XBAR-ADMAIF17-16 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 17: tegra-dlink-17 XBAR-ADMAIF18-17 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 18: tegra-dlink-18 XBAR-ADMAIF19-18 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: APE [NVIDIA Jetson Orin NX APE], device 19: tegra-dlink-19 XBAR-ADMAIF20-19 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```
