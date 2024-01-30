
def get_python_versions(min_version,max_version):
    version=tuple(map(int,min_version.split(".")))
    max_version=tuple(map(int,max_version.split(".")))
    versions=[]
    while version <= max_version:
        versions.append(".".join(map(str,version)))
        version=tuple([*version[:-1],version[-1]+1])

    return versions



