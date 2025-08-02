# primer3GUI
primer3GUI, or P3G for short, is a lightweight interface built using [Streamlit](https://streamlit.io/) that wraps around [Primer3](https://github.com/primer3-org/primer3)(V0.4.0), installable via Conda. This wrapper offers an alternative to the publicly available Primer3 web application with a couple of additional features to the original web application.

P3G was originally designed for cases where the web application would be unavailable or for design without an internet connection. P3G produces identical primer sequences for given inputs and parameters.

In rare cases, you may notice **minor differences in the total number of designs returned** compared to other Primer3 interfaces (e.g., the official web-based tools), despite using the same input parameters as specified in the official Primer3 repository. 





⚠️ **Note:** This project is not affiliated with or endorsed by the Primer3 development team.


## Features
This application offers similar functions and parameters for primer and probe design to the standard web application, with a couple of additional features. It offers:
- A web-based GUI for filling in parameters 
- Settings files with the specified input sequences and parameters that can be downloaded and reloaded so that specific designs can be saved and reviewed at a later date
- Outputs that can be saved in PDF or HTML format


## Licenses
This project is licensed under the MIT license. See the [LICENSE](LICENSE) for full terms.

Primer3 is included in this project and is licensed separately under the GNU General Public License v2.0.
See the Primer3 project [here](https://github.com/primer3-org/primer3) for full source code and license.

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mgils4/primer3GUI.git
cd primer3GUI
```

2. Create and activate the Conda environment:
```bash
conda env create -f primer3GUI_env.yml
conda activate primer3GUI
```

3. Install Primer3 (required separately):
```bash
conda install primer3=2.6.1
```

4. Run the python script via Streamlit
```bash
streamlit run 
```
TODO: fill in script name!


## Disclaimer
This is an independent tool wrapper of the Primer3 core engine.
It is not developed, maintained, or endorsed by the official Primer3 development team.
All trademarks and copyrights belong to their respective holders. 

## Citation 
If you use P3G in your research or projects, please cite this repository as follows:

Max van Gils, primer3GUI: A Streamlit GUI wrapper for Primer3, GitHub repository
https://github.com/mgils4/primer3GUI, [2025]

Please also cite the original primer3 papers and/or repository:  
> Untergasser A, Cutcutache I, Koressaar T, et al. Primer3—new capabilities and interfaces. Nucleic acids research 2012. DOI: 10.1093/nar/gks596.
> Koressaar T and Remm M. Enhancements and modifications of primer design program Primer3. Bioinformatics 2007. DOI: 10.1093/bioinformatics/btm091.
> https://github.com/primer3-org/primer3