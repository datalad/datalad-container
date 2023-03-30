from datalad.support.external_versions import external_versions

def get_container_command():
    for command in ["apptainer", "singularity"]:
        container_system_version = external_versions[f"cmd:{command}"]
        if container_system_version:
            return command
    else:
        raise RuntimeError("Did not find apptainer or singularity")


