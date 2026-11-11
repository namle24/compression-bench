package vn.usth.cbd;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

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
 * Application 2 (CPU-bound): each record is hashed with iterated SHA-256
 * and the scores are summed per city. The shuffle carries only a few KB.
 */
public class HashScore extends Configured implements Tool {

    public static class ScoreMapper extends Mapper<NullWritable, Text, Text, LongWritable> {

        private final Text city = new Text();
        private final LongWritable score = new LongWritable();
        private MessageDigest md;
        private int rounds;

        @Override
        protected void setup(Context ctx) throws IOException {
            rounds = ctx.getConfiguration().getInt("hashscore.rounds", 200);
            try {
                md = MessageDigest.getInstance("SHA-256");
            } catch (NoSuchAlgorithmException e) {
                throw new IOException(e);
            }
        }

        @Override
        protected void map(NullWritable key, Text value, Context ctx)
                throws IOException, InterruptedException {
            md.update(value.getBytes(), 0, value.getLength());
            byte[] d = md.digest();
            for (int i = 1; i < rounds; i++) {
                d = md.digest(d);
            }
            String s = value.toString();
            int a = s.indexOf('|');
            int b = s.indexOf('|', a + 1);
            int c = s.indexOf('|', b + 1);
            city.set(s.substring(b + 1, c));
            score.set(Long.numberOfLeadingZeros(ByteBuffer.wrap(d).getLong()));
            ctx.write(city, score);
        }
    }

    @Override
    public int run(String[] args) throws Exception {
        if (args.length != 2) {
            return Jobs.usage("HashScore");
        }
        Job job = Jobs.create(getConf(), "hashscore", HashScore.class, args[0], args[1]);
        job.setMapperClass(ScoreMapper.class);
        job.setCombinerClass(LongSumReducer.class);
        job.setReducerClass(LongSumReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(LongWritable.class);
        return job.waitForCompletion(true) ? 0 : 1;
    }

    public static void main(String[] args) throws Exception {
        System.exit(ToolRunner.run(new Configuration(), new HashScore(), args));
    }
}
