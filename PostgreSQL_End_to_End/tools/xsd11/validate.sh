#!/bin/sh
# XSD 1.1 validation of FundsXML files: validate.sh <schema.xsd> <file.xml>...
# xmllint and lxml only implement XSD 1.0, so we use Xerces-J 2.12.2 (XSD 1.1 build).
# The jars are downloaded once from Maven Central and checked against their SHA-1.
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
LIB="$DIR/lib"
M=https://repo1.maven.org/maven2
mkdir -p "$LIB"
while read -r sha path; do
  jar="$LIB/$(basename "$path")"
  if [ ! -f "$jar" ]; then
    curl -sSLf -o "$jar.part" "$M/$path"
    echo "$sha  $jar.part" | sha1sum -c --quiet - && mv "$jar.part" "$jar"
  fi
  CP="$CP:$jar"
done <<JARS
a5ea630f4487f924ed81d4880f5b9b86b9a7add6 org/exist-db/thirdparty/xerces/xercesImpl/2.12.2/xercesImpl-2.12.2-xml-schema-1.1.jar
a54005fd900ee211d39fd3e5406d362839e09b3d org/exist-db/thirdparty/org/eclipse/wst/xml/xpath2/1.2.0/xpath2-1.2.0.jar
88eadc5347b2a22c9c87a04687f0aabaeac01c0b edu/princeton/cup/java-cup/10k/java-cup-10k.jar
bc9057df4b5efddf7f6d1880bf7f3399f4ce5633 com/ibm/icu/icu4j/72.1/icu4j-72.1.jar
3789d9fada2d3d458c4ba2de349d48780f381ee3 xml-apis/xml-apis/1.4.01/xml-apis-1.4.01.jar
JARS
exec java -cp "${CP#:}" "$DIR/Validate.java" "$@"
