"""
MC Structure cleaner
By: Nyveon

v: 1.1
Modded structure cleaner for minecraft. Removes all references to non-existent
structures to allow for clean error logs and chunk saving.
"""

# Using Python 3.9 annotations
from __future__ import annotations

# Imports
import time  # for progress messages

# Efficient iteration
import itertools as it

# Argument parsing
from argparse import ArgumentParser, Namespace

# Filesystem interaction
from pathlib import Path

# Multiprocessing
from multiprocessing import Pool, cpu_count

# anvil-parser by matcool
from anvil import Region, Chunk, EmptyRegion

VERSION = "1.2"


def sep():
    """Print separator line"""
    print("----------------------------------")


# Dealing with files
def _load_region(region_path: Path) -> tuple[Region, str]:
    """Loads a region from a file"""
    return Region.from_file(str(region_path.resolve())), region_path.name


def _save_region(region: Region, dst: Path) -> None:
    """Saves a region to a file"""
    region.save(str(dst.resolve()))


# Removing Tags
def remove_tags_region(
    tags: set[str], region: Region, coords: tuple[int, int]
) -> tuple[Region, int]:
    """Remove tags in to_replace from the src region
    Write changes to dst/src.name"""
    start: float = time.perf_counter()
    count: int = 0

    new_region = EmptyRegion(*coords)

    # Check chunks
    for chunk_x, chunk_z in it.product(range(32), repeat=2):
        # Chunk Exists
        if region.chunk_location(chunk_x, chunk_z) != (0, 0):
            data = region.chunk_data(chunk_x, chunk_z)

            for tag in data["Level"]["Structures"]["Starts"].tags:
                if tag.name in tags:
                    del data["Level"]["Structures"]["Starts"][tag.name]
                    count += 1

            for tag in data["Level"]["Structures"]["References"].tags:
                if tag.name in tags:
                    del data["Level"]["Structures"]["References"][tag.name]
                    count += 1

            # Add the modified chunk data to the new region
            new_region.add_chunk(Chunk(data))

    end: float = time.perf_counter()
    print(f"{count} instances of tags removed in {end - start:.3f} s")

    return (new_region, count)


def _process_regions(tag: set[str], dst: Path, tup: tuple[Region, str]) -> int:
    region, name = tup

    _, x_loc, z_loc, _ = name.split(".")
    coords = (int(x_loc), int(z_loc))

    region, count = remove_tags_region(tag, region, coords)

    _save_region(region, dst / name)

    return count


def remove_tags(tags: set[str], src: Path, dst: Path, jobs: int) -> None:
    """Removes tags from src region files and writes them to dst"""
    start = time.perf_counter()
    count = None

    with Pool(processes=jobs) as pool:
        regions = pool.imap_unordered(_load_region, src.iterdir())
        data = zip(it.repeat(tags), it.repeat(dst), regions)
        count = sum(pool.starmap(_process_regions, data))

    end = time.perf_counter()

    sep()
    print(f"Done!\nRemoved {count} instances of tags: {tags}")
    print(f"Took {end - start:.3f} seconds")


# Environment
def setup_environment(new_region: Path) -> bool:
    """Try to create new_region folder"""
    if new_region.exists():
        print(f"{new_region.resolve()} exists, this may cause problems")
        proceed = input("Do you want to proceed regardless? [y/N] ")

        return proceed.startswith("y")

    new_region.mkdir()
    print(f"Saving newly generated region files to {new_region.resolve()}")

    return True


#  CLI
def get_args() -> Namespace:
    """Get CLI Arguments"""
    jobs = cpu_count() // 2

    prog_msg = f"MC Structure cleaner\nBy: Nyveon\nVersion: {VERSION}"
    tag_help = "The EXACT structure tag name you want removed (Use NBTExplorer\
            to find the name)"
    jobs_help = f"The number of processes to run (default: {jobs})"
    source_help = "The region folder (default world/region)"
    destination_help = "The destination folder (default new_regions)"

    parser = ArgumentParser(prog=prog_msg)

    parser.add_argument("-t", "--tag", type=str, help=tag_help, required=True)
    parser.add_argument("-j", "--jobs", type=int, help=jobs_help, default=jobs)
    parser.add_argument("--src", help=source_help, default="world/region")
    parser.add_argument("--dst", help=destination_help, default="new_region")

    return parser.parse_args()


def _main() -> None:
    args = get_args()

    to_replace = args.tag
    new_region = Path(args.dst)
    world_region = Path(args.src)
    num_processes = args.jobs

    print(f"Replacing {to_replace} in all region files.")
    sep()

    if not world_region.exists():
        print(f"Couldn't find {world_region.resolve()}")
        return None

    if not setup_environment(new_region):
        print("Aborted, nothing was done")
        return None

    n_to_process = len(list(world_region.iterdir()))

    remove_tags({to_replace}, world_region, new_region, num_processes)

    sep()
    print(f"Processed {n_to_process} files")
    print(f"You can now replace {world_region} with {new_region}")

    return None


if __name__ == "__main__":
    _main()
