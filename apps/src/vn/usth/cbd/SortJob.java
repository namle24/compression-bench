package vn.usth.cbd;

import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Partitioner;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Application 1 (I/O-bound): total-order sort of all records.
 * Almost no computation; the whole dataset is read, shuffled and written back.
 */
public class SortJob extends Configured implements Tool {

    public static class KeyMapper extends Mapper<NullWritable, Text, Text, NullWritable> {
        @Override
        protected void map(NullWritable key, Text value, Context ctx)
                throws IOException, InterruptedException {
            ctx.write(value, NullWritable.get());
        }
    }

    /** Records start with a uniform random hex id, so ranges on the first byte are balanced. */
    public static class HexRangePartitioner extends Partitioner<Text, NullWritable> {
        @Override
        public int getPartition(Text key, NullWritable value, int n) {
            int b = Character.digit(key.charAt(0), 16) * 16 + Character.digit(key.charAt(1), 16);
            return b * n / 256;
        }
    }

    public static class EmitReducer extends Reducer<Text, NullWritable, NullWritable, Text> {
        @Override
        protected void reduce(Text key, Iterable<NullWritable> values, Context ctx)
                throws IOException, InterruptedException {
            for (NullWritable ignored : values) {
                ctx.write(NullWritable.get(), key);
            }
        }
    }

    @Override
    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            return Jobs.usage("SortJob");
        }
        Job job = Jobs.create(getConf(), "sort", SortJob.class, args[0], args[1]);
        job.setMapperClass(KeyMapper.class);
        job.setPartitionerClass(HexRangePartitioner.class);
        job.setReducerClass(EmitReducer.class);
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(NullWritable.class);
        job.setOutputKeyClass(NullWritable.class);
        job.setOutputValueClass(Text.class);
        return job.waitForCompletion(true) ? 0 : 1;
    }

    public static void main(String[] args) throws Exception {
        System.exit(ToolRunner.run(new Configuration(), new SortJob(), args));
    }
}
