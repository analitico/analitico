
# Documentation

Internal rumblings, thoughts, ideas, evaluations of options related to building API documents for the project.

Run documentation site locally:  
`mkdocs serve`

To build the documentation:  
`mkdocs build`

### MkDocs  
Among all the tools that we evaluated for documentation we choose MkDocs because in the end you've got to start somewhere and this seemed fairly easy and a good way to get moving. Also there's no complex toolchain to install and it just works.  
Pros:
- documentation is outside the code so tech writer can easily take over
- documentation can be structured with more of a storyline and only document what is useful
- easy to serve as static content
- can easily be themed (see below for choosen material design theme)
https://www.mkdocs.org/

Material Design Theme for MkDocs   
https://github.com/squidfunk/mkdocs-material  
Documentation (and example)      
https://squidfunk.github.io/mkdocs-material/


## More tools (evaluated)

### Read the Docs
https://docs.readthedocs.io/en/stable/  
Pros:
- can be used to publish docs made with MkDocs
- wide adoption in open source community
- works with simple markdown
- supports hosting, versioning, etc
Cons:
- no live examples  
Getting started with mkdocs:  
https://docs.readthedocs.io/en/stable/intro/getting-started-with-mkdocs.html  


### Slate  
Pros:
- nice three column layout
- choice of themes/styles
- seems to be widely adopted
- based on fairly simple markdown
Cons:
- requires ruby on rails and additional tooling
- no dynamic documentation (eg: try live endpoint)
https://github.com/lord/slate  


### Shins
Shins is slate in node.js  
https://github.com/Mermade/shins  


### ReDoc  
Pros:
- (sort of) implemented already 
- https://staging.analitico.ai/redoc/#operation/tokens_read  


### API Docs  
Pros:
- supports markdown
- supports live examples
Cons:
- doesn't see to read our swagger file
- pricing
https://api-docs.io/  


### Swagger  
Pros:
- automatically generated from code
- already tried and built in comments
Cons:
- not easy to write long examples and explanation in code
- mixing code and tech docs may not be a good idea in the long run
- makes it harder for tech writer to edit
- exposes all endpoints automatically generating lots of unstructured clutter



## Articles

Free and Open Source API Documentation Tools  
https://pronovix.com/blog/free-and-open-source-api-documentation-tools



## Examples  

Giphy: Nice design, live API testing:  
https://giphy.api-docs.io  
https://help.stoplight.io/api-v1/versions/export  