// Run an XQuery against FundsXML via the Saxon s9api (native Java, no JAXB).
//
//   tools/fetch-tools.sh
//   SCP=.lib/Saxon-HE-12.5.jar:.lib/xmlresolver-5.2.2.jar:.lib/xmlresolver-5.2.2-data.jar
//   javac -cp "$SCP" -d /tmp/xq XQuery_Examples/invocation/RunXQuery.java
//   java  -cp "$SCP:/tmp/xq" RunXQuery <query.xq> <input.xml> [k=v ...]
// Exit: 0 success, 2 setup error.
//
// Dependencies: Saxon-HE + xmlresolver jars only (fetched by
//   tools/fetch-tools.sh into .lib/); no other libraries.
//
// This is a generic, FundsXML-agnostic XQuery runner: it binds the input as
// the context item and passes string external variables — the FundsXML
// specifics (no XML namespace, Position↔Asset by UniqueID) live in the .xq
// files it runs. s9api is Saxon's idiomatic Java API; no JAXB.
//
// External query variables are passed as k=v args (string-typed), e.g. n=5.

import java.io.File;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.QName;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XQueryCompiler;
import net.sf.saxon.s9api.XQueryEvaluator;
import net.sf.saxon.s9api.XQueryExecutable;
import net.sf.saxon.s9api.XdmAtomicValue;

public class RunXQuery {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("usage: RunXQuery <query.xq> <input.xml> [k=v ...]");
            System.exit(2);
        }
        try {
            Processor proc = new Processor(false);
            XQueryCompiler comp = proc.newXQueryCompiler();
            XQueryExecutable exe = comp.compile(new File(args[0]));
            XQueryEvaluator qe = exe.load();

            qe.setSource(new javax.xml.transform.stream.StreamSource(new File(args[1])));
            for (int i = 2; i < args.length; i++) {
                int eq = args[i].indexOf('=');
                if (eq > 0) {
                    qe.setExternalVariable(new QName(args[i].substring(0, eq)),
                                           new XdmAtomicValue(args[i].substring(eq + 1)));
                }
            }
            Serializer out = proc.newSerializer(System.out);
            out.setOutputProperty(Serializer.Property.INDENT, "yes");
            qe.run(out);
        } catch (Exception e) {
            System.err.println("error: " + e.getMessage());
            System.exit(2);
        }
    }
}
