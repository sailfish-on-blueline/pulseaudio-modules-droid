import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src/droid/droid-source.c"

HARNESS = r"""
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

typedef struct { unsigned rate; unsigned channels; } pa_sample_spec;
typedef struct { pa_sample_spec sample_spec; } pa_source;
typedef struct { void *mempool; } pa_core;
typedef struct { size_t length; unsigned char data[4096]; } pa_memblock;
typedef struct { pa_memblock *memblock; size_t index; size_t length; } pa_memchunk;
struct userdata {
    pa_core *core;
    pa_source *source;
    void *stream;
    void *resampler;
    size_t buffer_size;
    uint64_t timestamp;
    bool stream_valid;
};
static pa_memblock block;
static ssize_t read_result;
static unsigned posted;
static const uint64_t clock_now = 1000000;
static void unsuspend(struct userdata *u) { (void)u; }
static pa_memblock *pa_memblock_new(void *pool, size_t size) {
    (void)pool;
    block.length = size;
    return &block;
}
static void *pa_memblock_acquire(pa_memblock *b) { return b->data; }
static size_t pa_memblock_get_length(pa_memblock *b) { return b->length; }
static void pa_memblock_release(pa_memblock *b) { (void)b; }
static void pa_memblock_unref(pa_memblock *b) { (void)b; }
static void pa_silence_memory(void *p, size_t size, const pa_sample_spec *spec) {
    (void)spec;
    memset(p, 0, size);
}
static void pa_source_post(pa_source *source, pa_memchunk *chunk) {
    (void)source;
    (void)chunk;
    posted++;
}
static ssize_t pa_droid_stream_read(void *stream, void *p, size_t size) {
    (void)stream;
    (void)p;
    (void)size;
    return read_result;
}
static uint64_t pa_bytes_to_usec(size_t bytes, const pa_sample_spec *spec) {
    return (uint64_t)bytes * 1000000 / (spec->rate * spec->channels * 2);
}
static uint64_t pa_rtclock_now(void) { return clock_now; }
static void pa_resampler_run(void *resampler, pa_memchunk *input, pa_memchunk *output) {
    (void)resampler;
    (void)input;
    output->length = 0;
    output->memblock = NULL;
}
#define pa_log(...) ((void)0)
"""

MAIN = r"""
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    const int scenario = atoi(argv[1]);
    const ssize_t results[] = { -1, -1, 0, 128 };
    pa_core core = { 0 };
    pa_source source = { { 48000, 2 } };
    struct userdata u = { .core = &core, .source = &source, .buffer_size = 4096,
                          .timestamp = clock_now, .stream_valid = scenario != 0 };
    read_result = results[scenario];
    thread_read(&u);
    const uint64_t expected = clock_now + pa_bytes_to_usec(
        scenario == 3 ? (size_t)read_result : u.buffer_size, &source.sample_spec);
    const unsigned expected_posts = scenario == 0 || scenario == 3;
    if (u.timestamp != expected || posted != expected_posts) {
        fprintf(stderr, "scenario %d timestamp %llu expected %llu, posts %u expected %u\n",
                scenario, (unsigned long long)u.timestamp, (unsigned long long)expected,
                posted, expected_posts);
        return 1;
    }
    return 0;
}
"""


class PulseAudioInputPacingTests(unittest.TestCase):
    def test_input_failures_wait_for_the_next_buffer(self):
        if not SOURCE.is_file():
            self.skipTest("Build the matching PulseAudio input source before running its regression check")
        compiler = shutil.which("cc")
        self.assertIsNotNone(compiler)
        source = SOURCE.read_text()
        start = source.index("static int thread_read(struct userdata *u)")
        end = source.index("static void thread_func(", start)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            fixture = path / "input-read.c"
            binary = path / "input-read"
            fixture.write_text(HARNESS + source[start:end] + MAIN)
            subprocess.run([compiler, "-std=c11", str(fixture), "-o", str(binary)], check=True)
            for scenario in range(4):
                with self.subTest(scenario=scenario):
                    result = subprocess.run([str(binary), str(scenario)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
