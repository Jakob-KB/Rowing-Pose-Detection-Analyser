# Rowing-Pose-Detection-Analyser

[Migrating to BlazePose implmentation with MediaPipe]

The Pose Detection Algorithm is designed to take a minute-long video of someone using a rowing machine (otherwise known as an Erg) that can then be processed for numerous
analytics on the specific user's technique such as their ratio of stroke to recovery, the angle their body opens up during the rowing stroke and much more. Being an open-source
program anyone with the relevant skills may also tweak the code to allow any other analytics to be recorded. The following tools were used to develop the analyser:

 - Python
 - TensorFlow 
 - Torch
 - Pandas
 - MatPlotLib

Below you can see a screenshot of a user rowing (as you can see the video is taken from the side at ~3m back from the rowing machine) this specific video is of stock 
rowing footage although the software has been tested and opterated on numerous users such as myself and my other teammates.

![image](https://user-images.githubusercontent.com/50581493/142087383-226df071-a9a0-4e75-8716-1b0e55105d90.png)


Once the video has been processed the output looks like the follow, the word up the top indicates the part of the stroke the rower is in (drive or recovery) the ratio next is how long is spent in the drive compared to the time spent in the recovery, the spm is the 'strokes per minute' and is indicated to a tenth, finally the number located by the rowers hip is the current angle of her back to the erg and can help indicate if the rower is getting the maximum amount of power avalible.

![image](https://user-images.githubusercontent.com/50581493/142087072-3b37f476-4cfd-4176-8edf-3748d9c07eab.png)
