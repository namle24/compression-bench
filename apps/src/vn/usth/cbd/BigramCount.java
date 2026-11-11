package vn.usth.cbd;

import java.io.IOException;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.lib.reduce.LongSumReducer;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;

/**
 * Application 3 (balanced): counts word bigrams in the comment field.
 * Tokenization costs CPU and the high key cardinality keeps a large shuffle.
 */
public class BigramCount extends Configured implements Tool {

    public static class BigramMapper extends Mapper<NullWritable, Text, Text, LongWritable> {

        private static final LongWritable ONE = new LongWritable(1);
        private final Text bigram = new Text();

        @Override
        protected void map(NullWritable key, Text value, Context ctx)
                throws IOException, InterruptedException {
            String s = value.toString();
            String[] w = s.substring(s.lastIndexOf('|') + 1).split(" ");
            for (int i = 0; i + 1 < w.length; i++) {
                bigram.set(w[i] + ' ' + w[i + 1]);
                ctx.write(bigram, ONE);
            }
        }
    }

    @Override
    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            return Jobs.usage("BigramCount");
        }
        Job job = Jobs.create(getConf(), "bigram", BigramCount.class, args[0], args[1]);
        job.setMapperClass(BigramMapper.class);
        if (getConf().getBoolean("bigram.combiner", true)) {
            job.setCombinerClass(LongSumReducer.class);
        }
        job.setReducerClass(LongSumReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(LongWritable.class);
        return job.waitForCompletion(true) ? 0 : 1;
    }

    public static void main(String[] args) throws Exception {
        System.exit(ToolRunner.run(new Configuration(), new BigramCount(), args));
    }
}
