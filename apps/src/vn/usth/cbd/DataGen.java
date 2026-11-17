package vn.usth.cbd;

import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.fs.FileSystem;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.lib.input.NLineInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.SequenceFileOutputFormat;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Map-only generator. Each task writes one file smaller than an HDFS block,
 * so every codec yields the same number of input splits.
 */
public class DataGen extends Configured implements Tool {

    static final long BYTES_PER_TASK = 100L << 20;

    public static class GenMapper extends Mapper<LongWritable, Text, NullWritable, Text> {

        private final Text record = new Text();

        @Override
        protected void map(LongWritable key, Text value, Context ctx)
                throws IOException, InterruptedException {
            String[] p = value.toString().split(" ");
            int task = Integer.parseInt(p[0]);
            long bytes = Long.parseLong(p[1]);
            long seed = ctx.getConfiguration().getLong("datagen.seed", 2026L);
            RecordGenerator gen = new RecordGenerator(seed * 1_000_003L + task);
            long written = 0;
            while (written < bytes) {
                record.set(gen.next());
                ctx.write(NullWritable.get(), record);
                written += record.getLength() + 1;
            }
        }
    }

    @Override
    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: DataGen [-D key=value ...] <sizeMB> <output>");
            return 2;
        }
        long total = Long.parseLong(args[0]) << 20;
        Path out = new Path(args[1]);
        Configuration conf = getConf();

        // no leading underscore: FileInputFormat would skip the file
        Path ctl = new Path(out.getParent(), "ctl-" + out.getName());
        FileSystem fs = ctl.getFileSystem(conf);
        try (PrintWriter w = new PrintWriter(
                new OutputStreamWriter(fs.create(ctl, true), StandardCharsets.UTF_8))) {
            for (int i = 0; total > 0; i++) {
                long b = Math.min(BYTES_PER_TASK, total);
                w.println(i + " " + b);
                total -= b;
            }
        }

        Job job = Job.getInstance(conf, "datagen " + args[0] + "MB");
        job.setJarByClass(DataGen.class);
        job.setMapperClass(GenMapper.class);
        job.setNumReduceTasks(0);
        job.setInputFormatClass(NLineInputFormat.class);
        NLineInputFormat.setNumLinesPerSplit(job, 1);
        NLineInputFormat.addInputPath(job, ctl);
        job.setOutputFormatClass(SequenceFileOutputFormat.class);
        job.setOutputKeyClass(NullWritable.class);
        job.setOutputValueClass(Text.class);
        FileOutputFormat.setOutputPath(job, out);

        boolean ok = job.waitForCompletion(true);
        fs.delete(ctl, false);
        return ok ? 0 : 1;
    }

    public static void main(String[] args) throws Exception {
        System.exit(ToolRunner.run(new Configuration(), new DataGen(), args));
    }
}
