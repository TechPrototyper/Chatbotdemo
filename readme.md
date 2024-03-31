
# Beschreibung des Chatbot-Repositories

## Überblick

Der Chatbot setzt sich aus drei Hauptkomponenten sowie dem Browser zusammen. Im Folgenden werden die einzelnen Komponenten und deren Zusammenwirken beschrieben.

### Komponenten

1. **Bot Web App**: Entwickelt mit JavaScript und React, nutzt diese Webanwendung Material UI und React für Eingabe und Darstellung. Die Laufzeitumgebung für die Frontend Web-App ist eine serverless Azure Static Web App. Der Quellcode wird im Branch *Frontend* verwaltet. Dort übernommene Änderungen werden automatisch mittels einen Github Action Scripts in die Laufzeitumgebung deployed.

2. **Chatbotdemo Web API**: Der Middletier empfängt die Nachrichten aus der Webapp per API-Aufruf, und verarbeitet die Nachrichten; er stellt den Kontext zu früheren Gesprächen her, und modifiziert das Prompt, damit das Backend-LLM individuell auf den Benutzer eingehen kann. Eine eigene Klasse verknüpft dazu die UserId bzw. E-Mail Adresse des Anwenders mit einer Gesprächsverlaufs-Id von OpenAI, was das Wiedererkennen und Fortsetzen von Benutzerdialogen ermöglicht. Die Konversationen selbst werden direkt bei OpenAI gespeichert. Die Kommunikation mit OpenAI wird in einer Interaction-Klasse gekapselt. Die API ist als serverless Azure Function App in Python 3.10 implementiert. Sie nutzt das Azure Functions Framework 2.0, das ähnlich wie FastAPI die Routen auch über Dekoratoren bestimmt. Anders als FastAPI gibt es keine Parameterdeklaration, und auch deshalb keine automatische OpenAPI-Oberfläche bzw. ein OpenAPI-File. Dem helfen wir durch das Azure API Management ab, siehe unten. Man kann auch mit Hilfe des ASGI-Bridge FastAPI Apps als Azure Function App deployen, aber für diesen Overhead war hier kein Bedarf. Die API befindet sich ebenfalls im Repository im Branch *API*. Änderungen werden per CI/CD mit einem Github Action Script automatisch in die Function App der Cloud hochgeladen.

3. **OpenAI Backend**: Nutzt die Assistant API von OpenAI, basierend auf dem GPT-4 Turbo Modell, um die Konversationen zu verarbeiten. Grundsätzlich könnte auch hier das Azure OpenAI Backend genutzt werden. Zur Entwicklungszeit bestand grundsätzlich Zugriff auf Azure OpenAI, und lt. Microsoft Dokumentation ist das hier verwendete Assistant API in mehreren Locations online, darunter z.B. France Central, Sweden Central und East US. Leider sind alle Versuche, mit dorthin deployten Azure OpenAI Ressourcen einen Assistant zu hinterlegen, gescheitert. Die Deployments wurden zwar durchgeführt, aber die Assistants haben nie geantwortet, schon in der Azure OpenAI Studio Oberfläche im Assistant Playground nicht, und per API Aufruf leider auch nicht. Hier lässt sich aber mit Microsoft evtl. ein Ticket öffnen, um das Backend kurzfristig von OpenAI auf Microsoft umzustellen - die Logik der API ist prinzipiell dieselbe, bzw. auch in Einzelheiten.

Das Zusammenwirken der Komponenten ist in nachfolgenden UML Sequenzdiagramm dokumentiert:

![318154719-3f7b1530-9e21-4712-941c-7291b6d3ee60-2](https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/24cb80fc-4301-40d0-aee2-a0af598da52a)

**UML-Sequenzdiagramm**: Veranschaulicht die Interaktionen zwischen den Komponenten des Demo-Chatbots.

### Zusätzliche Infrastruktur

Vor den Middletier bzw. die Web API wurde ein API Gateway (Azure API Management) geschaltet, um den Zugriff zu steuern und einzuschränken. Hierbei wurde die OpenAPI-Spezifikation manuell so angepasst, dass die API vollständig beschrieben wurde, inkl. aller nötigen Parameter. Zwar sind Azure Function Apps und API Management integriert, und der Endpunkt der Function App kann automatisch ins APIM übernommen werden. Leider sind allerdings z.B. die Query Parameter nicht automatisch in den Metadaten enthalten, wie man dies z.B. von FastAPI kennt. Daher wurde das OpenAPI File, in Azure API Management *Frontend* genannt (hat nichts mit unserem Chatbot Fronend zu tun), entsprechend angepasst und vervollständigt.

<img width="1609" alt="318154925-24350a91-d626-40b0-aefd-2eb66c3397b0-2" src="https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/228c139e-7a8f-4dc9-b453-a1f963b27ac6">

<img width="1610" alt="318154906-83dedc77-5b3f-433c-9ecd-ad0c3d830758-2" src="https://github.com/TechPrototyper/Chatbotdemo/assets/110817746/b380dc5e-94fc-4152-8e6f-2edc70c9f88b">


**Azure API Management Screenshots**: Zeigen die eingebettete Chatbot Middle Tier API und einen Blick auf die modifizierte OpenAPI Datei.
