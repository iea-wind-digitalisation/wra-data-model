Contributing
============

## Issue Tracking

New feature requests, changes, enhancements, non-methodology features, and bug reports can be filed as new issues in the
[GitHub.com issue tracker](https://github.com/IEA-Task-43/digital_wra_data_standard/issues) at any time. Please be sure to fully describe the
issue.

<!---For other issues, please email the Task 43 distribution list at `xx`.--->

## Repository

The digital WRA digital_wra_data_standard repository is hosted on GitHub, and located here: https://github.com/IEA-Task-43/digital_wra_data_standard

This repository is organized using a modified git-flow system. Branches are organized as follows:

- master: Stable release version. Must have good test coverage and may not have all the newest features.
- dev: Development branch which contains the newest features. Tests must pass, but code may be unstable.
- feature/xxx: Branch from dev, should reference a GitHub issue number.

To work on a feature, please fork or clone digital_wra_data_standard locally. If your 
git status is unclean after you clone  (e.g., lots of untracked files and changes), chances are you are dealing with a 
Unicode normalization issue (specifically, the Unicode decomposition of filenames under macOS). This can be an issue on 
project with contributors using a mix of MacOS, Linux, and Windows. To resolve it, delete your clone. Then issue 
`git config --global core.precomposeunicode true` and clone your fork again. 

Once you have successfully cloned, create a feature branch from the `dev` branch. A feature branch should deal with 
only 1 issue from the Issue Log and ideally the feature branch name should contain this Issue id. Work out of this feature 
branch and commit changes locally before submitting a pull request. Commit messages should also contain the Issue id you are 
working, on preceded by '#' e.g. `git commit -m "iss #170 add length of diagonal brace"`. The `#170` allows GitHub to link the 
commit message to the specific Issue.

Typical files that are modified when working on an Issue are:
- The [data model](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/schema/iea43_wra_data_model.schema.json) itself
- The [demo file](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/demo_data/iea43_wra_data_model.json) implementation
- The [create SQL](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/tools/iea43_wra_data_model_postgresql.sql) statements
- The [Pydantic data model](tools/pydantic_model), which is generated from the JSON Schema and must be regenerated rather than edited by hand
- The [CHANGELOG.md](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/CHANGELOG.md)

Be sure to periodically synchronize the upstream `dev` branch into your feature branch to avoid conflicts in the pull request. 
GitHub will prompt you to create a pull request back to the original project after the first push from your feature branch to 
your fork. You can continue to iterate on your feature branch until you are ready to submit your pull request.

When the feature branch is ready, make a pull request into the `dev` branch of IEA-Task-43/digital_wra_data_standard through 
the GitHub.com UI. Do not create a pull request into the `master` branch. You will need to accept the Contributor License 
Agreement(CLA) for pull requests greater than 20 lines in length. [CLA Language](https://gist.github.com/Dynorat/231c6d3bc1e75b4e44bcb8b241686e93)

[![CLA assistant](https://cla-assistant.io/readme/badge/IEA-Task-43/digital_wra_data_standard)](https://cla-assistant.io/IEA-Task-43/digital_wra_data_standard)


## Pull Request

Pull requests must be made for any changes to be merged into the `dev` or `master` branches.
They must include updated documentation and pass all unit tests and integration tests.
In addition, code coverage should not be negatively affected by the pull request.

Only the `dev` branch should be merged into the `master` branch and all feature branches should be merged into the `dev` branch. Once 
sufficient updates have been reviewed, a new release will be made by merging the `dev` branch into the `master` branch.

**Scope:** Encapsulate the changes of one issue at a time.
It is greatly preferable to submit three small pull requests than it is to submit one large pull request.
Write a complete description of these changes in the pull request body.

**Tests:**
For any changes to the JSON schema, the contributor should

* Make sure that the changes result in a valid JSON schema
* Adjust the [demo file](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/demo_data/iea43_wra_data_model.json) to reflect any changes to the Schema. 
Tools like [jsonschemavalidator](https://www.jsonschemavalidator.net/) can help with these tasks where the Schema can be pasted 
on the left and the demo file on the right. If it is valid the green tick with "No errors found. JSON validates against the schema" will be shown.
* Ensure that the PostgreSQL create table SQL statements contained in [iea43_wra_data_model_postgresql.sql](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/tools/iea43_wra_data_model_postgresql.sql)
are compatible with the adjusted Schema. If relevant, update the demo data SQL statements too [iea43_wra_data_model_demo_data.sql](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/demo_data/iea43_wra_data_model_demo_data.sql).
* Regenerate the Pydantic data model by running `poetry run poe generate` from the `tools/pydantic_model` directory, and commit the result. The model is generated from the JSON Schema and is never edited by hand. The 'Python Model Build, Lint, and Test' pipeline does not produce the committed model; it regenerates a copy of its own purely to compare, and fails if the two differ. A schema change that has not been carried into the model will therefore not pass review.

**Documentation:** TBD
<!---Include any relevant changes to inline documentation, as well as any changes to the RST files located in /sphinx.--->

**Changelog:** For pull requests that encapsulate a user-facing feature, or is significant to users of digital_wra_data_standard 
for some other reason, please add a line to [CHANGELOG.md](https://github.com/IEA-Task-43/digital_wra_data_standard/blob/master/CHANGELOG.md) 
in the [Unreleased] section, including linking to the Issue.


<!--- ## Documentation Style
TBD
Documentation is written using RST, and is located both inline and within the /sphinx directory.
Any changes to the analysis methodology should be discussed there or offline. Once a methodology change is decided,
create new tickets in this repository towards implementing the change.-->

<!--- ## Testing
TBD but may define guidelines for validating the schema
All code should be paired with a corresponding unit or integration test.
digital_wra_data_standard uses pytest and the built in unittest framework.
For instructions on running tests, please see the [Readme](testing link).-->

## Maintaining the Pydantic Data Model

The [Pydantic data model](tools/pydantic_model) is a Python implementation of the _WRA Data Model_, generated from the JSON Schema. It is never edited by hand. A manual change survives only until the next regeneration, and the pipeline rejects it before then.

### Regenerating after a schema change

Run the following from the `tools/pydantic_model` directory and commit the result alongside the schema change:

```bash
poetry run poe generate
```

That command generates the model with a pinned set of code generator flags, applies the post-generation patches described below, and formats the result with `ruff`. The one-time environment setup is described in the [Pydantic data model README](tools/pydantic_model/README.md).

The generated model is committed to the repository because it is the file that users import, so it has to be present rather than built on demand. The 'Python Model Build, Lint, and Test' pipeline does not produce that file. It regenerates a copy of its own, purely to compare against the committed one, and fails if the two differ. A schema change that has not been carried into the model therefore cannot pass review.

Regenerating as part of the change also puts the resulting API change in front of a reviewer. A field becoming required, or an enum value disappearing, is a breaking change for anyone using the model, and it is visible in the pull request diff rather than appearing after the change has been merged.

`datamodel-code-generator` and `ruff` are pinned to exact versions rather than version ranges, because both determine the content of the generated file. Upgrading either is therefore a deliberate change: raise the version, regenerate, and review the resulting diff.

### When a property cannot be generated correctly

Some JSON Schema constructs cannot be expressed by the code generator. The fix always belongs in the generation process, never in the model file. In order of preference:

1. **Set a code generator flag.** Most cases are solved this way and need no custom code. The flags, each with the reason it is set, are listed in `CODEGEN_FLAGS` in [generate_model.py](tools/pydantic_model/generate_model.py). For example, the generator maps the `date-time` format to a timezone-aware type by default, which rejects every timestamp in the _WRA Data Model_ because the UTC offset is carried separately in `offset_from_utc_hrs`. Setting `--output-datetime-class datetime` corrects this.
2. **Add a post-generation patch.** Where no flag exists, add a patch function to [generate_model.py](tools/pydantic_model/generate_model.py). Two exist already: `uniqueItems` on arrays, which the generator drops silently, and `description` and `title` on a property that is a bare `$ref` carrying a default, which the generator omits. Both read their values from the JSON Schema rather than restating them, so neither can fall out of step with the specification, and both fail the build if any expected site is missing.
3. **Change the JSON Schema.** Appropriate only where the schema construct is itself ambiguous or incorrect. The specification should not be altered merely to suit a code generator.

### Testing a new constraint

Most failures are loud. The code generator exits with an error, a patch function fails if an expected site is missing, and the test suite validates every file in [demo_data](demo_data) against the model.

A constraint that is silently weakened is the exception. Where a schema change adds a restriction such as a pattern, a bound or a uniqueness rule, and no demo file violates it, nothing fails even though the model is wrong. Add a test to [test_model.py](tools/pydantic_model/tests/test_model.py) proving that an invalid value is rejected, rather than only that valid data still passes. The existing tests for duplicate array items and for malformed `classification` values show the pattern.

## Creating a GitHub Release

When creating a release, make sure the tag follows the format: `vX.X.X-YYYY.MM`. This format is used in URLs, so 
it's important to maintain consistency across all releases.

Attach the relevant JSON Schema file as a release asset. This ensures a fixed, versioned copy of the schema that 
cannot be modified later. In code pipelines do not link to the file in the master (or main) branch, as that version 
may continue to receive updates not yet included in an official release. It is recommended to link to this file
added in the release.

In the release description, include:
- A brief paragraph summarising the main additions or changes in this release.
- The full changelog content for the release (copied from the project changelog).
- Include the changelog from the Digital Calibration Certificate or the Floating Lidar File Format if any changes were made since the last release.

Finally, review all details to ensure accuracy, then publish the release.
