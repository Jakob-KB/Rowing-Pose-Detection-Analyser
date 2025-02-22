# Rowing Pose Detection Analyzer  

**Migrating to a BlazePose implementation with MediaPipe**  

This tool processes a minute-long video of a person using a rowing machine (Ergometer) to analyze their technique. It provides key performance metrics:  

- **Stroke-to-recovery ratio** – Time spent in the drive vs. recovery phase.  
- **Body angle** – The rower’s back angle relative to the Erg, indicating power generation.  
- **Strokes per minute (SPM)** – Measured to one decimal place.  

Being open-source, it allows developers to modify the code and add new analytics.  

## Tools & Technologies  

- Python  
- TensorFlow  
- PyTorch  
- Pandas  
- Matplotlib  

## Sample Output  

### Input: Rowing Video  
The software processes videos taken from the **side (~3m from the Erg)**. Below is an example of a test video.  

![Rowing Input](https://user-images.githubusercontent.com/50581493/142087383-226df071-a9a0-4e75-8716-1b0e55105d90.png)  

### Processed Output  
The software overlays performance metrics on the video:  

- **Stroke phase** (Drive or Recovery)  
- **Stroke-to-recovery ratio**  
- **SPM (Strokes Per Minute)**  
- **Back angle** relative to the Erg  

These help identify inefficiencies and areas for improvement.  

![Rowing Output](https://user-images.githubusercontent.com/50581493/142087072-3b37f476-4cfd-4176-8edf-3748d9c07eab.png)  

## Future Improvements  

- **Switching to BlazePose (MediaPipe)** for better pose estimation.  
- **Adding a GUI** to simplify video uploads and analysis.  
- **More metrics** like handle speed and slide position tracking.  

## Contributing  

Contributions are welcome. Open an issue or submit a pull request to improve the model or add features.  

## License  

This project is open-source under the **MIT License**.
