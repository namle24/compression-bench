package vn.usth.cbd;

import java.util.Arrays;
import java.util.Random;

/**
 * Synthetic sales records: id|date|city|product|price|qty|comment.
 * Comments use a Zipf-distributed vocabulary so the data compresses like real text.
 */
public class RecordGenerator {

    private static final String[] CITIES = {
        "Hanoi", "HoChiMinh", "DaNang", "HaiPhong", "CanTho", "Hue", "NhaTrang", "Paris",
        "Toulouse", "Lyon", "Marseille", "Nice", "Bordeaux", "Lille", "Tokyo", "Seoul",
        "Bangkok", "Singapore", "Berlin", "Madrid"
    };
    private static final int VOCAB_SIZE = 20000;
    private static final String[] VOCAB = new String[VOCAB_SIZE];
    private static final double[] CDF = new double[VOCAB_SIZE];
    private static final char[] HEX = "0123456789abcdef".toCharArray();

    static {
        Random r = new Random(42);
        double sum = 0;
        for (int i = 0; i < VOCAB_SIZE; i++) {
            char[] w = new char[2 + r.nextInt(9)];
            for (int j = 0; j < w.length; j++) {
                w[j] = (char) ('a' + r.nextInt(26));
            }
            VOCAB[i] = new String(w);
            sum += 1.0 / (i + 1);
            CDF[i] = sum;
        }
        for (int i = 0; i < VOCAB_SIZE; i++) {
            CDF[i] /= sum;
        }
    }

    private final Random rnd;
    private final StringBuilder sb = new StringBuilder(256);

    public RecordGenerator(long seed) {
        this.rnd = new Random(seed);
    }

    public String next() {
        sb.setLength(0);
        long id = rnd.nextLong();
        for (int s = 60; s >= 0; s -= 4) {
            sb.append(HEX[(int) (id >>> s) & 0xF]);
        }
        sb.append("|2025-");
        pad2(1 + rnd.nextInt(12));
        sb.append('-');
        pad2(1 + rnd.nextInt(28));
        sb.append('|').append(CITIES[rnd.nextInt(CITIES.length)]);
        sb.append("|P").append(10000 + rnd.nextInt(90000));
        int cents = 100 + rnd.nextInt(99900);
        sb.append('|').append(cents / 100).append('.');
        pad2(cents % 100);
        sb.append('|').append(1 + rnd.nextInt(20)).append('|');
        int words = 8 + rnd.nextInt(17);
        for (int i = 0; i < words; i++) {
            if (i > 0) {
                sb.append(' ');
            }
            sb.append(word());
        }
        return sb.toString();
    }

    private String word() {
        int i = Arrays.binarySearch(CDF, rnd.nextDouble());
        return VOCAB[i >= 0 ? i : Math.min(-i - 1, VOCAB_SIZE - 1)];
    }

    private void pad2(int v) {
        if (v < 10) {
            sb.append('0');
        }
        sb.append(v);
    }
}
