## Modules Directory Structure
The modules directory holds all module configurations and optionally all module data. A 'module' in the modules directory can simply be a YAML configuration that points to another directory in the backend machine or it can be a folder with a YAML configuration inside.

## Internal Module Naming Conventions
Due to the different naming conventions of the different languages used, each part of the system uses different formats. For example, the front facing name of a module can be `Test Module`. This would make the server/backend (Python) name `test_module`, any URL endpoints `test-module`, and any server/frontend (TypeScript) name `testModule`.

## Adding Addition Modules
Modules can be added through the backend endpoint `/user/modules/add`
