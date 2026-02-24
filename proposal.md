Project Proposal Outline

- Heading:   
  - Title   
    - OpenCourt Stats  
  - Team Name   
    - OpenCourt  
  - Team Members   
    - Kenneth Hinman | Alex Worthington | Jackson Murphy | Samuel Bombrys  
- Section 1: Introduction    
  - What is the project?   
    - We want to create a full-stack web app that pulls data from the CBBData API and other similar sources. With the data, we hope to synthesize useful data visualizations for data analysis and if we have the time we would like to build further on this and begin training a predictive model to make team and player predictions for this ongoing season.  
  - What is the motivation for the project?  
    -  We enjoy watching and analyzing sports and have often faced paywalls for these types of sites.  
  - Place your project in the context of the market   
    - There are similar products in the market to ours but mostly function on subscription models blocking basic users from   
  - Is your project idea novel?   
    - The idea is not necessarily novel as there are plenty of websites that provide these statistics, with more advanced ones behind a paywall.  
  - If so, what need does it fill?   
    - The one thing it could do differently is more user-friendly statistics and possibly the type of model used for predictions.  
  - If not novel, what existing software does it resemble?   
    - [EvanMiya.com](http://EvanMiya.com)  
    - CBB Analytics  
  - How is it different?   
    - We won’t lock everything behind paywalls. We want to make our analysis and projections public so casual sports fans can view them.  
  - What are the backgrounds of the team members?   
    - Some of the team members' backgrounds include web-development, web scraping, machine learning, statistics, and general software development.  
  - Is there anything you’d like to include to orient the reader?  
    - Assuming we are making a website to show the statistics, we would want the site to correctly guide the user without any need of a tutorial. An optional one may be provided.  
- Section 2: Customer Value  
  - Customer Need  
    - Our target audience is a college basketball fan (ages 18-35) who engages in bracket              contests (such as March Madness), follows discussions of advanced statistics on the              internet, and is hungry for more information without having to pay for a subscription to         advanced analytics tools. College basketball fans who are casual or semi-serious fans do         not have access to advanced efficiency statistics and forecasting tools because the best         tools available are behind paywalls. They are forced to rely on basic statistics (such as        points per game, winning percentage) that do not accurately measure a team's quality. 
  - Proposed Solution  
    - OpenCourt Stats will offer free access to advanced team efficiency analysis, interactive         graphics, and a transparent predictive model for college basketball games. The service           will focus on ease of use and will enable users to compare teams, examine trends, and            display prediction results without the need for a subscription.
  - Measures of Success  
    - Achieve at least 200 unique users during March Madness.
    - At least 30% of users return for 3 or more sessions.
    - Average session time ≥ 3 minutes.
    - User survey rating of prediction usefulness ≥ 4/5.
    - Prediction accuracy exceeding baseline (e.g., outperforming simple win-percentage model). 
- Section 3: Proposed Solution & Technology  
  - System: technology you deliver  
    - Basic web application that displays CBB stats/data and provides analysis based on a predictive model
┌───────────────────────────┐
│   External CBBData API    │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│      Django Backend       │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│   Data Processing Layer   │
│  - Cleaning               │
│  - Feature Engineering    │
│  - Predictive Model       │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│      SQLite Database      │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│       REST Endpoints      │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│ Frontend (Tailwind UI)    │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│ ApexCharts Visualizations │
└──────────────┬────────────┘
               ↓
┌───────────────────────────┐
│           User            │
└───────────────────────────┘
  - Tools: technology you use to build what you deliver   
    - We will probably use web-development tools such as HTML for the webpage and python for the statistics and predictive models.  
    - Python 3.11+ & Libraries  
    - Django 5.x  
    - HTML \+ Tailwind CSS \+ DaisyUI  
    - ApexCharts  
    - requests (API calls)  
    - Git/GitHub  
    - SQLite (built-in to Django for ORM)  
- Section 4: Team   
  - Skills  
    - Has anyone on the team built something like this before?  
      - Kenneth: built an early stage CFB dashboard for displaying CFB data using Django. The project is not finished but provides basic infrastructure that can be implemented in this project.  
      - Jackson: built a web scraper that extracts stock market news, forum discussions, and sentiment indicators and used AI to analyze data (python), built basic ground up machine learning models (JS), basic web dev experience with limited framework experience (HTML,CSS)  
      - Alex: experience working for a web development company. Proficient in HTML/CSS/Bootstrap with a basic understanding of PHP/JS.  
      - Samuel: Experience with machine learning and deep learning models through python. Built a chrome extension to analyze the safety of websites.  
    - Are the tools known or new to the team?  
      - At least someone on the team has individual experience with each tool but little experience in combining everything into a single project  
  - Roles  
    - Project Manager: Kenneth  
    - UI/UX Designers (Rotating)  
    - Developers (Rotating)  
    - QA Engineers (Rotating)  
- Section 5: Project Management  
  - Schedule   
    - Deadlines:  
      - Proposal due: \~2/17  
      - Proposal Revision: \~2/24  
      - Min viable and status report 1: \~3/10  
      - Improve and status report 2: \~3/24  
      - Testing and refine report 3: \~4/10  
      - Complete project, report, and presentation: \~4/14  
  - Constraints   
    - Ethical: people using our data for personal financial decisions   
    - Legal: NO  
  - Resources   
    - API and scraping should allow us to collect the amount of good data we need to begin analysis and data display   
  - Descoping   
    - If we aren't able to reach all of our goals, such as prediction and analysis, a basic website that displays data and has a good user experience will still allow us to reach some of the goals we set out to achieve 
