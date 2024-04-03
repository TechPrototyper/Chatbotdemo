
# Repo Chatbotdemo - Kurzdoku

## Anleitung zur Benutzung

Die bekannte Bot-URL aufrufen. Dann soll ein Name und eine E-Mail Adresse angegeben werden. Die E-Mail Adresse, die angegeben wird, und auch fiktiv sein kann, wird als Schlüssel verwendet, um den Dialog zu persistieren bzw. später wieder aufzurufen. Man kann also den Dialog beenden und zu einem späteren Zeitpunkt wieder fortsetzen.

## Überblick über die Komponenten

Der Demo Chatbot setzt sich aus drei Hauptkomponenten sowie dem Browser zusammen. Im Folgenden werden die einzelnen Komponenten und deren Zusammenwirken beschrieben.

### Komponenten

1. **Web App**: Entwickelt mit JavaScript und React, nutzt diese Webanwendung Material UI und React für Eingabe und Darstellung. Die Laufzeitumgebung für die Frontend Web-App ist eine serverless Azure Static Web App. Der Quellcode wird im Branch *Frontend* verwaltet. Dort übernommene Änderungen werden automatisch mittels eines Github Action Scripts in die Laufzeitumgebung deployed. Das Script kann im Branch *Frontend* unter den Github Workflows eingesehen werden.

2. **Web API**: Der Middletier empfängt die Nachrichten aus der Webapp per API-Aufruf, und verarbeitet die Nachrichten; er stellt den Kontext zu früheren Gesprächen her, und modifiziert das Prompt, damit das Backend-LLM individuell auf den Benutzer eingehen kann. Eine eigene Klasse verknüpft dazu die UserId bzw. E-Mail Adresse des Anwenders mit einer Gesprächsverlaufs-Id von OpenAI, was das Wiedererkennen und Fortsetzen von Benutzerdialogen ermöglicht. Die Konversationen selbst werden direkt bei OpenAI gespeichert. Die API ist als serverless Azure Function App in Python 3.10 implementiert. Sie nutzt das Azure Functions Framework 2.0, das ähnlich wie FastAPI die Routen auch über Dekoratoren direkt im Python Code bestimmt. Anders als FastAPI gibt es keine Parameterdeklaration in den Dekoratoren bzw. Injection in die Methoden, und deshalb keine automatische OpenAPI Oberfläche oder Datei. Dem wird durch das Azure API Management abgeholfen, siehe unten. Die API befindet sich ebenfalls im Repository im Branch *API*. Änderungen werden per CI/CD mit einem Github Action Script, das man im Branch unter den Workflows findet, automatisch in die Function App in der Cloud deployed. 

3. **Azure OpenAI Backend**: Nutzt die Assistant API von OpenAI, basierend auf dem GPT-4 Turbo Modell, um die Konversationen zu verarbeiten. Der Assistant ist mit System-Prompts "programmiert" darauf, den Anwender rund um das Thema Energie in Hamburg zu unterstützen. Er ist angehalten, den Gesprächsfokus auch immer wieder dorthin zu lenken, und bei Erfolglosigkeit das Gespräch ggf. auch zu beenden. Das (Azure-) OpenAI Assistant API ist sehr flexibel, von seinen zahlreichen Funktionen werden hier in der Demo nur wenige genutzt. Besonders interessant ist die Trennung von Konversation und Run im neuen API, die dazu führt, dass man einen einzelnen Gesprächsstrang grundsätzlich auch mit mehreren LLMs bzw. Assistants führen kann. Die API ermöglicht ohne weitere Tools die Gestaltung komplexer Interaktionen zwischen Anwender, verschiedenen Modellen und verschiedenen Systemen wie internen Datenbanken, Vektordatenbanken, externen APIs. Die Entwicklunng und die meisten Tests wurden auf dem Backend von OpenAI durchgeführt, die aktuelle Version ist nun auf Azure OpenAI deployed. Da die Assistant API bislang nicht überall verfügbar ist, wurde France Central als nächstes Azure Rechenzentrum mit Assistant API Funktion ausgewählt.

Das Zusammenwirken der Komponenten ist vereinfacht in nachfolgenden UML Sequenzdiagramm dokumentiert:

![318154719-3f7b1530-9e21-4712-941c-7291b6d3ee60-2](https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/24cb80fc-4301-40d0-aee2-a0af598da52a)

**UML-Sequenzdiagramm**: Veranschaulicht die Interaktionen zwischen den Komponenten des Demo-Chatbots.

### Zusätzliche Infrastruktur

Vor den Middletier bzw. die Web API wurde ein API Gateway (Azure API Management) geschaltet, um den Zugriff zu steuern und einzuschränken. Hierbei wurde die OpenAPI-Spezifikation manuell so angepasst, dass die API vollständig beschrieben wurde, inkl. aller nötigen Parameter. Zwar sind Azure Function Apps und API Management integriert, und der Endpunkt der Function App kann automatisch ins APIM übernommen werden. Leider sind allerdings z.B. die Query Parameter nicht automatisch in den Metadaten enthalten, wie man dies z.B. von FastAPI kennt. Daher wurde das OpenAPI File, in Azure API Management *Frontend* genannt (hat nichts mit unserem Chatbot Fronend zu tun), entsprechend angepasst und vervollständigt.

<img width="1609" alt="318154925-24350a91-d626-40b0-aefd-2eb66c3397b0-2" src="https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/228c139e-7a8f-4dc9-b453-a1f963b27ac6">

<img width="1610" alt="318154906-83dedc77-5b3f-433c-9ecd-ad0c3d830758-2" src="https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/b380dc5e-94fc-4152-8e6f-2edc70c9f88b">


**Azure API Management Screenshots**: Zeigen die eingebettete Chatbot Middle Tier API und einen Blick auf die modifizierte OpenAPI Datei.

### Events: New User Registered Event im Azure Event Grid

Der Chatbot enthält serverseitig ein Eventgrid-Topic, auf dem zur Zeit für den Fall eines Erstlogins ein Ereignis ausgelöst wird. Mit Hilfe einer Eventgrid Subscription kann dann auf dieses Ereignis reagiert werden. Es ist sind weitere Events geplant, aber die Infrastruktur steht. Es muss dazu natürlich ein Eventgrid-Topic angelegt werden, und zwei weitere Environment-Parameter gesetzt werden, damit die Chat API Events veröffentlichen kann. Zur Behandlung wurde eine Familie von Klassen erstellt, die die Nachrichten nach dem Cloud Event Schenma 1.0 generieren, *my_cloudevents.py*, und ein Modul, welches diese Event-Messages an das Event-Grid übermittelt, *event_grid_publisher.py*.


### Runtime und Repo-Variablen

Um dieses Beispiel in einer anderen Umgebung zum Laufen zu bringen, muss in Microsoft Azure eine Function App für eine Python 3.10 App angelegt werden. Der Name der Function App muss später, siehe unten, in einer Variablen hinterlegt werden. Eine Function App erzeugt außerdem ein sog. Publishing Profile, über das Deployments gesteuert werden. Man kann das Publishing Profile herunterladen und einbetten, siehe ebenfalls unten, und in einem Secret speichern, siehe unten. Wir benötigen außerdem für den Fall, dass CI/CD eingerichtet werden soll, eine Application Registration; diese erzeugt eine ClientId, ein ClientSecret und stellt z.B. bei Generierung durch die Kommandozeile eine JSON-Datei bereit, die wir als Secret AZURE_CREDENTIALS hinterlegen, siehe unten.

Die Function App muss außerdem konfiguriert werden, und zwar so, dass alle wichtigen Informationen vorliegen. Für diese Demo wurde auf den Einsatz eines Key Vaults verzichtet, alle nötigen Parameter, sowohl für das Azure OpenAI Backend, als auch für das von OpenAI, wurden in der Function App Configuration Section eingerichtet. Hier nicht im Bild sind noch die 

![Screenshot 2024-04-03 at 18 47 38](https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/51ec448a-f178-4ae9-9f3f-287774e3c9b0)

**Azure Function App Configuration Screenshot:** Alle wichtigen Parameter wie Api-Keys, Connection Strings etc. müssen in der App Configuration hinterlegt werden.

Für das Frontend müssen wir eine Azure Static Web App anlegen. Diese kann man direkt mit einem Github Repo verbinden, und CI/CD wird automatisch eingerichtet. Aber Vorsicht, es sind in der automatisch erzeugten Datei einige Änderungen zu machen; bitte dazu einfach hier im Branch Frontend die Datei vergleichen.

Das Einrichten der Secrets und Variablen erfolgt unter

Settings...Secrets & Variables...Actions

folgende Einstellungen gemacht werden:

Secrets:

AZURE_APP_PUBLISH_PROFILE                  Das sog. Publishing Profile der Azure Function App
AZURE_CREDENTIALS                          Eine JSON-Datei, die ClientId, ClientSecret, SubscriptionId und TenantId enthält.

Ein weiteres Secret wird automatisch angelegt, wenn man die Azure Static Web App anlegt.

Variables:

AZURE_FUNCTIONAPP_NAME                    Der Name der Function App, in die die API deployed wird
AZURE_FUNCTIONAPP_PACKAGE_PATH            Die Stelle im Repo, in der der Quellcode für die API enthalten ist.

### Genutzte Technologien der Azure Plattform, und auf der Azure Plattform:

1. Azure Static Web App, HTML, JavaScript, React, Material UI Components (MUI), mit CI/CD via Github
2. Azure Function App mit Python 3.10, mit CI/CD via Github
3. Azure Storage Account, Azure Table Storage
4. Azure API Management, mit modifizierter OpenAPI-Spezifikation
5. Azure OpenAI Resource (France Central)
6. Azure OpenAI Assistant API
7. Azure Application Registration (für CI/CD mit Github Action Scripts)
8. Azure Event Grid
