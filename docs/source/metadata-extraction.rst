Metadata Extraction
*******************

If `datalad-metalad`_ extension is installed, `datalad-container` can
extract metadata from singularity containers images.

(It is recommended to use a tool like `jq` if you would like to read the
output yourself.)

Singularity Inspect
-------------------

Adds metadata gathered from `singularity inspect` and the version of
`singularity` or `apptainer`.

For example:

(From the ReproNim/containers repository)

`datalad meta-extract -d . container_inspect images/bids/bids-pymvpa--1.0.2.sing  | jq`

.. code-block:: 

  {
    "type": "file",
    "dataset_id": "b02e63c2-62c1-11e9-82b0-52540040489c",
    "dataset_version": "9ed0a39406e518f0309bb665a99b64dec719fb08",
    "path": "images/bids/bids-pymvpa--1.0.2.sing",
    "extractor_name": "container_inspect",
    "extractor_version": "0.0.1",
    "extraction_parameter": {},
    "extraction_time": 1680097317.7093463,
    "agent_name": "Austin Macdonald",
    "agent_email": "austin@dartmouth.edu",
    "extracted_metadata": {
      "@id": "datalad:SHA1-s993116191--cc7ac6e6a31e9ac131035a88f699dfcca785b844",
      "type": "file",
      "path": "images/bids/bids-pymvpa--1.0.2.sing",
      "content_byte_size": 0,
      "comment": "SingularityInspect extractor executed at 1680097317.6012993",
      "container_system": "apptainer",
      "container_system_version": "1.1.6-1.fc37",
      "container_inspect": {
        "data": {
          "attributes": {
            "labels": {
              "org.label-schema.build-date": "Thu,_19_Dec_2019_14:58:41_+0000",
              "org.label-schema.build-size": "2442MB",
              "org.label-schema.schema-version": "1.0",
              "org.label-schema.usage.singularity.deffile": "Singularity.bids-pymvpa--1.0.2",
              "org.label-schema.usage.singularity.deffile.bootstrap": "docker",
              "org.label-schema.usage.singularity.deffile.from": "bids/pymvpa:v1.0.2",
              "org.label-schema.usage.singularity.version": "2.5.2-feature-squashbuild-secbuild-2.5.6e68f9725"
            }
          }
        },
        "type": "container"
      }
    }
  }

.. _datalad-metalad: http://docs.datalad.org/projects/metalad/en/latest/
