// Run an XSLT 2.0 stylesheet via the Saxon s9api (native Java, no JAXB).
//
//   tools/fetch-tools.sh
//   SCP=.lib/Saxon-HE-12.5.jar:.lib/xmlresolver-5.2.2.jar:.lib/xmlresolver-5.2.2-data.jar
//   javac -cp "$SCP" -d /tmp/rt XSLT_Transformations/invocation/RunTransform.java
//   java  -cp "$SCP:/tmp/rt" RunTransform <stylesheet.xslt> <input.xml> <output> [k=v ...]
// Exit: 0 success, 2 setup error.
//
// Dependencies: Saxon-HE + xmlresolver jars only (fetched by
//   tools/fetch-tools.sh into .lib/); no other libraries.
//
// This is a generic, FundsXML-agnostic invocation wrapper: it applies any
// stylesheet to any XML and passes through string parameters (k=v) — the
// FundsXML specifics live in the .xslt files it runs. The repo's stylesheets
// are XSLT 2.0; Saxon supplies the engine. s9api is Saxon's idiomatic Java
// API — no JAXB involved (a full data binding would be needless here).

import java.io.File;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.QName;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XdmAtomicValue;
import net.sf.saxon.s9api.XsltCompiler;
import net.sf.saxon.s9api.XsltExecutable;
import net.sf.saxon.s9api.XsltTransformer;

public class RunTransform {
    public static void main(String[] args) {
        if (args.length < 3) {
            System.err.println("usage: RunTransform <xslt> <input.xml> <output> [k=v ...]");
            System.exit(2);
        }
        try {
            Processor proc = new Processor(false);
            XsltCompiler comp = proc.newXsltCompiler();
            XsltExecutable exe = comp.compile(new javax.xml.transform.stream.StreamSource(new File(args[0])));
            XsltTransformer t = exe.load();
            t.setSource(new javax.xml.transform.stream.StreamSource(new File(args[1])));
            for (int i = 3; i < args.length; i++) {
                int eq = args[i].indexOf('=');
                if (eq > 0) {
                    t.setParameter(new QName(args[i].substring(0, eq)),
                                   new XdmAtomicValue(args[i].substring(eq + 1)));
                }
            }
            Serializer out = proc.newSerializer(new File(args[2]));
            t.setDestination(out);
            t.transform();
            System.out.println("wrote " + args[2]);
        } catch (Exception e) {
            System.err.println("error: " + e.getMessage());
            System.exit(2);
        }
    }
}
