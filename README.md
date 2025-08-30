# primer3GUI
primer3GUI, or P3G for short, is a lightweight interface built using [Streamlit](https://streamlit.io/) that wraps around [Primer3](https://github.com/primer3-org/primer3)(V0.4.0), installable via Conda. This wrapper offers an alternative to the publicly available Primer3 web application with a couple of additional features to the original web application.

P3G was originally designed for cases where the web application for Primer3 vV0.4.0 would be unavailable or for design without an internet connection. P3G produces identical primer sequences for given inputs and parameters.

You may notice **minor differences in the total number of designs returned** compared to other Primer3 interfaces (e.g., the official web-based tools), despite using the same input parameters. This is due to P3G using a newer release of the primer3core (V 2.6.1), as the web version is using V 1.1.4. 

⚠️ **Note:** This project is not affiliated with or endorsed by the Primer3 development team and is purely a personal project.

<br>

## Features
This application offers similar functions and parameters for primer and probe design to the standard web application, with a couple of additional features. It offers:
- A web-based GUI for filling in parameters 
- Settings files with the specified input sequences and parameters that can be downloaded and reloaded so that specific designs can be saved and reviewed at a later date
- Outputs that can be saved in PDF or HTML format
- Creating results with pre-designed primers without having to alter all parameters to suit your designs, effectively overriding parameters but including warnings so the user can see what parameters do not fit with the provided design

Currently, a couple of different versions of the application exist. For the differences between them, see [here](P3G/README.md). 

<br>

## Licenses
This project is licensed under the MIT license. See the [LICENSE](LICENSE) for full terms.

Primer3 is included in this project and is licensed separately under the GNU General Public License v2.0.
See the Primer3 project [here](https://github.com/primer3-org/primer3) for full source code and license.

<br>

## Installation and Usage

1. Dowload this repository either as a ZIP and unpack, or via commandline:
```bash
git clone https://github.com/mgils4/primer3GUI.git
```
2. Navigate to the relevant directory:
```bash
cd primer3GUI/P3G
```

3. Create and activate the Conda environment:
```bash
conda env create -f P3G_conda_env.yml
conda activate P3G
```

4. Install Primer3 (required separately):
```bash
conda install primer3=2.6.1
```

5. Run the python script via Streamlit
```bash
streamlit run P3G_V1.0.py
```

6. Open the application in your preferred browser using one of the URLs that appear in the console. For security reasons, the Local URL is safer.

If no GUI appears or an error pops up, a reload of the page can fix this problem.

For an overview of how each of the currently implemented settings affect primer picking, see the [Settings explanation](P3G/Settings_explained.md).

<br>

## Disclaimer
This is an independent tool wrapper of the Primer3 core engine.
It is not developed, maintained, or endorsed by the official Primer3 development team.
All trademarks and copyrights belong to their respective holders. 

This application is currently only tested locally, not on a server based setting, and thus its functionality in a server-based or production environment cannot be guaranteed.

<br>

## Citation 
If you use P3G in your research or projects, please cite this repository as follows:

Max van Gils, primer3GUI: A Streamlit GUI wrapper for Primer3, GitHub repository
https://github.com/mgils4/primer3GUI, [2025]

Please also cite the original primer3 papers and/or repository:  
- Untergasser A, Cutcutache I, Koressaar T, et al. Primer3—new capabilities and interfaces. Nucleic acids research 2012. DOI: 10.1093/nar/gks596.
- Koressaar T and Remm M. Enhancements and modifications of primer design program Primer3. Bioinformatics 2007. DOI: 10.1093/bioinformatics/btm091.
- https://github.com/primer3-org/primer3

<br>

## Roadmap / TO DO

- incorporate a small popup for running the application using st.toast (waiting on an update from Streamlit)
- look into ways to better allow the user to switch between tabs
- potentially add an overview to visualize all the created oligo's on the target sequence
- add the legend to the exported result files
- add the standard libraries and allow user to add custom library sequences for detecting unexpected cross reactivity
- add penalty weight settings for determining the "optimal/best" primers. This would allow the user to change them from the default settings to custom settings
- rerender the warning and output tabs only when run is clicked again, so the result does not disappear after making changes (changes made, testing needed)
