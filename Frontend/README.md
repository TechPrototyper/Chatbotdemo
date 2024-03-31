
Der Chatbot besteht im Wesentlichen aus 3 Komponenten, und dem Browser. Diese sind:

	1. Bot Web App
	2. Bottie Web API
	3. OpenAI Backend, ein Assistant auf Basis des GPT-4 Turbo Modells

Die Bot Web App ist eine JavaScript/React App und nutzt zur Eingabe und Präsentation das Material UI und React; als Ablaufumgebung für die App dient eine serverless Azure Static Web App. Die Azure Static Web App ist mit dem Github Repo
REPO
verbunden, angenommene Änderungen führen zu einem automatischen Deployment der Web App.

Die Web API basiert auf drei Modulen, die in Python 3.10 entwickelt wurden. Das API läuft serverless als Azure Function, entwickelt mit dem neuen Functions Framework 2.0. Es liegt im Repo 
REPO
und ist mit CI/CD mit der Azure Function App vernetzt. Nach einer freigegebenen Änderung wird die Function App automatisch neu deployed.

Das Backend ist ein Assistant API von OpenAI. Dies ist grundsätzlich auch eins-zu-eins auf Azure OpenAI verfügbar, meine Tests mit dem Backend scheiterten aber, daher habe ich mich hier für OpenAI entschieden. Als Hilfsmodul dient noch eine kleine Klasse, die die vom Frontend übermittelte UserId/E-Mail Adresse mit einer Gesprächsverlaufs-Id von OpenAI verbindet; so werden Benutzerdialoge wiedererkannt, können referenziert und auch fortgesetzt werden. Die Konversationen selbst werden in OpenAI gespeichert, die Funktionalität wird vom Assistant API bereit gestellt. Dabei werden die Dialoge innerhalb des Backends unabhängig vom benutzten Assistant gespeichert.

Das folgende UML-Sequenzdiagramm zeigt vereinfacht die Funktionsweise des Chatbots:

![image](https://github.com/TechPrototyper/Botapi/assets/110817746/3f7b1530-9e21-4712-941c-7291b6d3ee60)

Außerdem habe ich noch ein API Gateway vor das Web API gesetzt, um den Zugang zum Web API zu steuern und zu restringieren. Dazu bietet sich Azure API Management (APIM) an. In APIM wurde die OpenAPI-Datei, dort "Frontend" genannt, so angepasst, dass sie die due API vollständig beschreibt, d.h. alle Parameterbeschreibungen, Beispiele uvm enthält, die leider aus der Function App nicht automatisch abgeleitet werden können. Der Komfort einer FastAPI Anwendung wird mit dem Standardprogrammiermodell von Microsoft hier nicht erreicht:

<img width="1610" alt="Screenshot 2024-03-30 at 01 19 59" src="https://github.com/TechPrototyper/Botapi/assets/110817746/83dedc77-5b3f-433c-9ecd-ad0c3d830758">

<img width="1609" alt="Screenshot 2024-03-30 at 01 20 37" src="https://github.com/TechPrototyper/Botapi/assets/110817746/24350a91-d626-40b0-aefd-2eb66c3397b0">


