package vn.usth.cbd;

import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.input.SequenceFileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.mapreduce.lib.output.SequenceFileOutputFormat;

/** Common setup: every application reads and writes block-compressible SequenceFiles. */
final class Jobs {

    private Jobs() {
    }

    static Job create(Configuration conf, String name, Class<?> main, String in, String out)
            throws IOException {
        Job job = Job.getInstance(conf, name);
        job.setJarByClass(main);
        job.setInputFormatClass(SequenceFileInputFormat.class);
        job.setOutputFormatClass(SequenceFileOutputFormat.class);
        FileInputFormat.addInputPath(job, new Path(in));
        FileOutputFormat.setOutputPath(job, new Path(out));
        return job;
    }

    static int usage(String app) {
        System.err.println("Usage: " + app + " [-D key=value ...] <input> <output>");
        return 2;
    }
}
