package vn.usth.cbd;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadMXBean;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.io.compress.CompressionCodec;
import org.apache.hadoop.io.compress.CompressionCodecFactory;
import org.apache.hadoop.io.compress.CompressionInputStream;
import org.apache.hadoop.io.compress.CompressionOutputStream;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Intrinsic codec characteristics on one core: ratio, (de)compression time and CPU time.
 * Usage: CodecBench [sampleMB] [repetitions]
 */
public class CodecBench extends Configured implements Tool {

    private static final String[] SPECS = {
        "snappy", "lz4", "gzip", "zstd:1", "zstd:3", "zstd:9", "zstd:19"
    };
    private static final ThreadMXBean THREADS = ManagementFactory.getThreadMXBean();

    @Override
    public int run(String[] args) throws Exception {
        int sizeMb = args.length > 0 ? Integer.parseInt(args[0]) : 256;
        int reps = args.length > 1 ? Integer.parseInt(args[1]) : 5;
        byte[] data = sample(sizeMb << 20);
        byte[] buf = new byte[1 << 16];

        System.out.println("codec,rep,orig_bytes,comp_bytes,ratio,comp_s,decomp_s,comp_cpu_s,decomp_cpu_s");
        for (String spec : SPECS) {
            String[] p = spec.split(":");
            Configuration conf = new Configuration(getConf());
            if (p.length > 1) {
                conf.setInt("io.compression.codec.zstd.level", Integer.parseInt(p[1]));
            }
            String name = p[0].equals("zstd") ? "zstandard" : p[0];
            CompressionCodec codec = new CompressionCodecFactory(conf).getCodecByName(name);
            String label = p.length > 1 ? p[0] + "-" + p[1] : p[0];

            for (int r = 0; r <= reps; r++) {
                ByteArrayOutputStream bos = new ByteArrayOutputStream(data.length / 2);
                long c0 = THREADS.getCurrentThreadCpuTime();
                long t0 = System.nanoTime();
                try (CompressionOutputStream out = codec.createOutputStream(bos)) {
                    out.write(data);
                }
                long t1 = System.nanoTime();
                long c1 = THREADS.getCurrentThreadCpuTime();
                byte[] comp = bos.toByteArray();

                long t2 = System.nanoTime();
                try (CompressionInputStream in = codec.createInputStream(new ByteArrayInputStream(comp))) {
                    while (in.read(buf) != -1) {
                        // drain
                    }
                }
                long t3 = System.nanoTime();
                long c3 = THREADS.getCurrentThreadCpuTime();

                if (r == 0) {
                    continue;
                }
                System.out.printf(Locale.ROOT, "%s,%d,%d,%d,%.4f,%.4f,%.4f,%.4f,%.4f%n",
                        label, r, data.length, comp.length, (double) data.length / comp.length,
                        (t1 - t0) / 1e9, (t3 - t2) / 1e9, (c1 - c0) / 1e9, (c3 - c1) / 1e9);
            }
        }
        return 0;
    }

    private static byte[] sample(int bytes) {
        RecordGenerator gen = new RecordGenerator(1);
        ByteArrayOutputStream out = new ByteArrayOutputStream(bytes + 1024);
        while (out.size() < bytes) {
            byte[] line = (gen.next() + "\n").getBytes(StandardCharsets.UTF_8);
            out.write(line, 0, line.length);
        }
        return out.toByteArray();
    }

    public static void main(String[] args) throws Exception {
        System.exit(ToolRunner.run(new Configuration(), new CodecBench(), args));
    }
}
