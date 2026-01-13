# LinkedIn Data Analysis Tool

A Python-based application designed to analyze exported LinkedIn data and generate clear, insightful visualizations about user activity, network growth, job search behavior, and professional trajectory.  
This project combines data cleaning, automated analysis, and a graphical interface to make LinkedIn data exploration accessible to all users — even without programming experience.

**Note:** The code contains comments in French for personal clarity, while all public documentation is provided in English.

---

## Features

### Activity Analysis

- Monthly and cumulative interaction trends  
- Comment vs reaction evolution  
- Activity heatmaps (day × time of day)  
- Seasonality and peak activity detection  

### Job Search Insights

- Saved job trends over time  
- Most targeted companies  
- Most frequent job titles  

### Professional Journey

- Timeline of professional experiences  
- Key indicators (duration, longest/shortest experience, etc.)  

### Network Analysis

- Sector distribution of connections  
- Monthly network growth  
- Key network indicators (growth rate, peak months, etc.)  

### User-Friendly Interface

- Tkinter-based GUI  
- Modular analysis selection  
- Progress tracking and error handling  

## Installation

Clone the repository and install dependencies:

git clone https://github.com/yourusername/linkedin-analysis-tool.git
cd linkedin-analysis-tool
pip install -r requirements.txt

### How to use 

- Export your LinkedIn data from your account settings.
- Extract the ZIP file and place the relevant CSV files inside the data/ directory.
- Launch the tool: python linkedin_analyse.py
- Use the interface to select the analyses you want to run.

## Data Folder

The tool expects LinkedIn CSV exports to be placed in the data/ directory.
For demonstration purposes, the repository includes anonymized example files that illustrate the expected structure.

Important:
- Do not upload personal LinkedIn data to GitHub.
- Use anonymized examples or keep the folder empty.

## Technologies Used

- Python
   - pandas — data cleaning and manipulation
   - matplotlib and seaborn — visualization
   - tkinter — graphical interface
- Data preprocessing and harmonization
- Automated exploratory analysis

## Academic Context

This project was developed as part of a Master’s program in Data Science (DS2E).

It demonstrates practical skills in:
- data cleaning and harmonization
- exploratory data analysis
- visualization design
- workflow automation
- GUI development
- reproducible research practices

The project was carried out in collaboration with Erleta MZIU and Chimene NOUICER.

## Limitations

LinkedIn exports vary depending on:
- language settings
- account activity
- LinkedIn updates

Additional considerations:
- Some analyses require specific files (for example, Comments.csv, Reactions.csv).
- Missing or inconsistent columns may require manual adjustments.
- No official documentation exists for LinkedIn’s export structure, requiring empirical exploration.

## Future Improvements

- Interactive dashboards (Plotly, Streamlit)
- Enhanced GUI design (custom themes, navigation)
- Export options for charts (PDF, PNG)
- Extended analysis for messages, posts, and login patterns
- Multi-user comparison mode
- Automated report generation (PDF/HTML)

## License

This project is released under the MIT License.
You are free to use, modify, and distribute it.

## Contributions

Contributions, suggestions, and improvements are welcome.
Feel free to open an issue or submit a pull request.

## Contact

SINANAJ Venera  
Master’s student in Data Science (DS2E)

This project is part of an ongoing learning process and may evolve over time.
