// GenerateTestKey — create a THROWAWAY self-signed RSA key + certificate for
// the XML-signature examples, using only the JDK's own `keytool`.
//
// This replaces the old openssl-based generate-test-key.sh: keytool ships with
// every JDK (keytool / keytool.exe), so this runs identically on Windows,
// Linux and macOS with no extra tool to install.
//
//   ./mvnw -q -pl XML_Signature/java compile exec:java \
//       -Dexec.mainClass=GenerateTestKey
//   (optional first arg: output directory; default XML_Signature/keys)
//
// Output (gitignored — never commit private keys, even demo ones):
//   test-signing.p12       PKCS#12 keystore  (alias: fundsxml, pass: changeit)
//   test-signing-cert.pem  public certificate (for verification)
//   test-signing-key.pem   PKCS#8 private key (for the xmlsec1 / signxml CLI
//                           and Python reference examples — emitted here, in
//                           pure JDK, so no openssl is needed on any OS)
//
// FOR DEMO USE ONLY — 2048-bit RSA, 10-year self-signed, hard-coded password.

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.util.Base64;

public class GenerateTestKey {

    static final String ALIAS = "fundsxml";
    static final String PASS  = "changeit";

    public static void main(String[] args) throws Exception {
        // Default to XML_Signature/keys relative to the working directory
        // (the repo root when launched via mvnw from the root).
        Path dir = Paths.get(args.length > 0 ? args[0]
                                              : "XML_Signature/keys");
        Files.createDirectories(dir);
        Path p12  = dir.resolve("test-signing.p12");
        Path cert = dir.resolve("test-signing-cert.pem");
        Path keyPem = dir.resolve("test-signing-key.pem");

        // keytool's genkeypair fails if the alias already exists, so start
        // from a clean keystore for idempotent re-runs.
        Files.deleteIfExists(p12);
        Files.deleteIfExists(cert);
        Files.deleteIfExists(keyPem);

        String keytool = keytool();

        run(keytool, "-genkeypair",
            "-alias", ALIAS,
            "-keyalg", "RSA", "-keysize", "2048",
            "-sigalg", "SHA256withRSA",
            "-validity", "3650",
            "-dname", "CN=fundsxml-test-signer, OU=Demo, "
                      + "O=FundsXML Examples, C=AT",
            "-keystore", p12.toString(), "-storetype", "PKCS12",
            "-storepass", PASS, "-keypass", PASS);

        // -rfc => Base64 PEM certificate (same content the old script's
        // test-signing-cert.pem held; used to pin verification).
        run(keytool, "-exportcert", "-rfc",
            "-alias", ALIAS,
            "-keystore", p12.toString(), "-storepass", PASS,
            "-file", cert.toString());

        // keytool cannot export a private key to PEM, so do it in pure JDK:
        // load the PKCS#12, take the RSA key, write it as an unencrypted
        // PKCS#8 PEM. xmlsec1 / signxml read this directly (no openssl).
        KeyStore ks = KeyStore.getInstance("PKCS12");
        try (var in = Files.newInputStream(p12)) {
            ks.load(in, PASS.toCharArray());
        }
        PrivateKey pk = (PrivateKey) ks.getKey(ALIAS, PASS.toCharArray());
        String b64 = Base64.getMimeEncoder(64, "\n".getBytes())
            .encodeToString(pk.getEncoded());   // PKCS#8 DER
        Files.writeString(keyPem,
            "-----BEGIN PRIVATE KEY-----\n" + b64
            + "\n-----END PRIVATE KEY-----\n");

        System.out.println("wrote: " + p12
            + " (alias=" + ALIAS + " pass=" + PASS + ")");
        System.out.println("       " + cert);
        System.out.println("       " + keyPem);
    }

    /** Locate the keytool that belongs to the running JDK (cross-platform). */
    static String keytool() {
        String home = System.getProperty("java.home");
        boolean win = System.getProperty("os.name", "")
                            .toLowerCase().contains("win");
        Path k = Paths.get(home, "bin", win ? "keytool.exe" : "keytool");
        return Files.isExecutable(k) ? k.toString() : "keytool";
    }

    /** Run a process, stream its output, and fail loudly on a non-zero exit. */
    static void run(String... cmd) throws Exception {
        Process p = new ProcessBuilder(cmd)
            .redirectErrorStream(true)
            .inheritIO()
            .start();
        int code = p.waitFor();
        if (code != 0) {
            System.err.println("keytool failed (exit " + code + "): "
                + String.join(" ", cmd));
            System.exit(2);
        }
    }
}
