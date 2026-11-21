# Pixel 3 audio input repair

This branch is based on upstream tag `14.2.110`, commit `7ca34ded1109f15965a0bb059590bbbdf26185ae` from `mer-hybris/pulseaudio-modules-droid`.

The input thread schedules the next buffer deadline after a failed stream reopen, a failed read or an empty read. This prevents immediate repeated retries when the input HAL cannot supply audio. The existing successful-read path is preserved.

The RPM spec builds the main, common and development packages from source with release `1.26.2.blueline`. PulseAudio module installation paths follow the PulseAudio version in the build environment. The main package satisfies the minimum version required by the Pixel 3 configuration.

Run the input pacing regression test with a C compiler available.

```sh
python3 -m unittest discover -s tests -v
```

For OBS, add a `pulseaudio-modules-droid` package to the Pixel 3 project and use the included `_service` file. It retrieves this branch through `tar_git`, including the RPM spec. Build with the Sailfish OS 5.2 PulseAudio development packages and Halium 12 dependencies. The source package produces a matching `pulseaudio-modules-droid-common` subpackage.

On the Pixel 3, the device configuration also supplies a PCM16-capable audio policy. The policy change and the input retry repair were validated together for recording and playback.
