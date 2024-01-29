location="doc-src"
instance="Writerside/atc"
artifact="webHelpATC2-all.zip"
workspace="project_directory_root"
imageVersion="232.10275"


docker run \
--platform linux/amd64 \
--rm -v ${workspace}:/github/workspace \
registry.jetbrains.team/p/writerside/builder/writerside-builder:${imageVersion} \
/bin/bash -c "export DISPLAY=:99; Xvfb :99 & /opt/builder/bin/idea.sh helpbuilderinspect -source-dir /github/workspace/${location} -product ${instance} --runner github -output-dir /github/workspace/artifacts/ || true; echo 'Test existing artifacts'; ls -la /github/workspace/artifacts/"
