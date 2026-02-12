#!/bin/bash
# ==============================================================================
# list-directory.sh - List files in a directory with metadata and pagination
# ==============================================================================
# Lists files with rich metadata (name, size, date, type). Two modes:
# - Summary mode (--summary): counts by type and age, total size
# - Listing mode (default): paginated file list with per-file metadata
#
# With --dirs-only, lists subdirectories instead of files:
# - Summary mode: counts total and uncategorized subdirectories
# - Listing mode: per-subdirectory metadata (size, items, contents breakdown)
# - Skips known category folders (Images/, Documents/, etc.)
#
# Uses extension-based type classification (fast, no mdls overhead).
# Only lists items at the top level (not recursive into subdirectories).
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/common.sh"

# Defaults
DIR="$HOME/Downloads"
OFFSET=0
LIMIT=50
SORT_BY="date"
SORT_ORDER="desc"
FILTER_TYPE=""
SUMMARY=false
INCLUDE_HIDDEN=false
DIRS_ONLY=false

# Category folder names to skip in dirs-only mode
CATEGORY_DIRS="Images Documents Spreadsheets Archives Installers Videos Audio Code Other"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)            DIR="$2"; shift 2 ;;
        --offset)         OFFSET="$2"; shift 2 ;;
        --limit)          LIMIT="$2"; shift 2 ;;
        --sort)           SORT_BY="$2"; shift 2 ;;
        --order)          SORT_ORDER="$2"; shift 2 ;;
        --filter-type)    FILTER_TYPE="$2"; shift 2 ;;
        --summary)        SUMMARY=true; shift ;;
        --include-hidden) INCLUDE_HIDDEN=true; shift ;;
        --dirs-only)      DIRS_ONLY=true; shift ;;
        *) error_exit "Unknown option: $1" ;;
    esac
done

# Expand ~ in directory path
DIR="${DIR/#\~/$HOME}"

# Validate directory
if [[ ! -d "$DIR" ]]; then
    error_exit "Directory not found: $DIR"
fi

# Check if a directory name is a known category folder
is_category_dir() {
    local name="$1"
    for cat in $CATEGORY_DIRS; do
        if [[ "$name" == "$cat" ]]; then
            return 0
        fi
    done
    return 1
}

# Collect subdirectories at top level (excluding DIR itself and category folders)
collect_dirs() {
    local find_args=("$DIR" -maxdepth 1 -type d '!' -path "$DIR")

    if [[ "$INCLUDE_HIDDEN" != true ]]; then
        find_args+=('!' -name '.*')
    fi

    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        local dname
        dname=$(basename "$d")
        if ! is_category_dir "$dname"; then
            echo "$d"
        fi
    done < <(find "${find_args[@]}" 2>/dev/null)
}

# Get extension breakdown for a directory (top 6 most common)
# Uses a pure pipeline for speed — no bash loop over individual files.
get_contents_summary() {
    local dir="$1"
    local result
    result=$(find "$dir" -type f 2>/dev/null \
        | sed 's/.*\///' \
        | awk -F. '{if (NF>1) print tolower($NF); else print "(none)"}' \
        | sort | uniq -c | sort -rn | head -6 \
        | awk '{printf "%s(%d), ", $2, $1}' \
        | sed 's/, $//')

    if [[ -z "$result" ]]; then
        echo "(empty)"
    else
        echo "$result"
    fi
}

# Extension-to-type classification
classify_extension() {
    local ext
    ext=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    case "$ext" in
        png|jpg|jpeg|heic|gif|svg|webp|ico|tiff|tif|bmp|raw|cr2|nef)
            echo "images" ;;
        pdf|doc|docx|txt|rtf|pages|odt|md|epub)
            echo "documents" ;;
        xls|xlsx|numbers|ods|csv|tsv)
            echo "spreadsheets" ;;
        zip|gz|tar|rar|7z|bz2|xz|tgz)
            echo "archives" ;;
        dmg|pkg|mpkg|iso)
            echo "installers" ;;
        app)
            echo "applications" ;;
        mp4|mov|avi|mkv|webm|m4v|wmv|flv)
            echo "videos" ;;
        mp3|wav|aac|m4a|flac|ogg|wma|aiff)
            echo "audio" ;;
        py|js|ts|html|css|json|xml|yaml|yml|sh|rb|go|rs|c|cpp|h|java|swift|kt)
            echo "code" ;;
        *)
            echo "other" ;;
    esac
}

# Human-readable size
human_size() {
    local bytes=$1
    if [[ $bytes -ge 1073741824 ]]; then
        awk "BEGIN { printf \"%.1f GB\", $bytes / 1073741824 }"
    elif [[ $bytes -ge 1048576 ]]; then
        awk "BEGIN { printf \"%.1f MB\", $bytes / 1048576 }"
    elif [[ $bytes -ge 1024 ]]; then
        awk "BEGIN { printf \"%.1f KB\", $bytes / 1024 }"
    else
        echo "${bytes} bytes"
    fi
}

# Friendly type description from extension
type_description() {
    local ext
    ext=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    case "$ext" in
        pdf) echo "PDF Document" ;;
        doc|docx) echo "Word Document" ;;
        xls|xlsx) echo "Excel Spreadsheet" ;;
        ppt|pptx) echo "PowerPoint Presentation" ;;
        txt) echo "Text File" ;;
        md) echo "Markdown File" ;;
        csv) echo "CSV Spreadsheet" ;;
        png) echo "PNG Image" ;;
        jpg|jpeg) echo "JPEG Image" ;;
        heic) echo "HEIC Image" ;;
        gif) echo "GIF Image" ;;
        svg) echo "SVG Image" ;;
        webp) echo "WebP Image" ;;
        mp4) echo "MP4 Video" ;;
        mov) echo "QuickTime Video" ;;
        mkv) echo "MKV Video" ;;
        mp3) echo "MP3 Audio" ;;
        wav) echo "WAV Audio" ;;
        m4a) echo "M4A Audio" ;;
        zip) echo "ZIP Archive" ;;
        gz|tgz) echo "Gzip Archive" ;;
        tar) echo "Tar Archive" ;;
        rar) echo "RAR Archive" ;;
        7z) echo "7-Zip Archive" ;;
        dmg) echo "Disk Image" ;;
        pkg|mpkg) echo "Installer Package" ;;
        iso) echo "ISO Disk Image" ;;
        app) echo "Application" ;;
        py) echo "Python Script" ;;
        js) echo "JavaScript File" ;;
        ts) echo "TypeScript File" ;;
        html) echo "HTML File" ;;
        css) echo "CSS File" ;;
        json) echo "JSON File" ;;
        xml) echo "XML File" ;;
        yaml|yml) echo "YAML File" ;;
        sh) echo "Shell Script" ;;
        rtf) echo "Rich Text File" ;;
        pages) echo "Pages Document" ;;
        numbers) echo "Numbers Spreadsheet" ;;
        epub) echo "EPUB Document" ;;
        *) echo "File" ;;
    esac
}

# Extensions belonging to each type category (for summary display)
type_extensions() {
    case "$1" in
        images)       echo "png, jpg, jpeg, heic, gif, svg, webp, ico, tiff, bmp" ;;
        documents)    echo "pdf, doc, docx, txt, rtf, pages, odt, md, epub" ;;
        spreadsheets) echo "xls, xlsx, numbers, ods, csv, tsv" ;;
        archives)     echo "zip, gz, tar, rar, 7z, bz2, xz, tgz" ;;
        installers)   echo "dmg, pkg, mpkg, iso" ;;
        applications) echo "app" ;;
        videos)       echo "mp4, mov, avi, mkv, webm, m4v" ;;
        audio)        echo "mp3, wav, aac, m4a, flac, ogg" ;;
        code)         echo "py, js, ts, html, css, json, xml, yaml, sh" ;;
        other)        echo "everything else" ;;
    esac
}

# Check if extension matches a filter type
matches_filter() {
    local ext="$1"
    local filter="$2"
    if [[ -z "$filter" ]]; then
        return 0
    fi
    local category
    category=$(classify_extension "$ext")
    [[ "$category" == "$filter" ]]
}

# Collect files at top level (depth 1, files only)
collect_files() {
    local find_args=("$DIR" -maxdepth 1 -type f)

    if [[ "$INCLUDE_HIDDEN" != true ]]; then
        find_args+=('!' -name '.*')
    fi

    find "${find_args[@]}" 2>/dev/null
}

# Get file extension (without dot, lowercased)
get_extension() {
    local name="$1"
    local ext="${name##*.}"
    if [[ "$ext" == "$name" ]]; then
        echo ""
    else
        echo "$ext" | tr '[:upper:]' '[:lower:]'
    fi
}

# ---- Dirs-Only Summary Mode ----
if [[ "$DIRS_ONLY" == true && "$SUMMARY" == true ]]; then
    echo "=== Directory Summary (subdirectories): $DIR ==="
    echo ""

    total_dirs=0
    uncategorized=0

    # Count all subdirs (including category folders)
    all_dirs_args=("$DIR" -maxdepth 1 -type d '!' -path "$DIR")
    if [[ "$INCLUDE_HIDDEN" != true ]]; then
        all_dirs_args+=('!' -name '.*')
    fi
    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        total_dirs=$((total_dirs + 1))
    done < <(find "${all_dirs_args[@]}" 2>/dev/null)

    # Count uncategorized (non-category) subdirs
    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        uncategorized=$((uncategorized + 1))
    done < <(collect_dirs)

    echo "Total: $total_dirs subdirectories"
    echo ""

    # Show which category folders exist
    existing_cats=()
    for cat in $CATEGORY_DIRS; do
        if [[ -d "$DIR/$cat" ]]; then
            existing_cats+=("$cat/")
        fi
    done
    if [[ ${#existing_cats[@]} -gt 0 ]]; then
        echo "Category folders (skipped): $(IFS=', '; echo "${existing_cats[*]}")"
    else
        echo "Category folders (skipped): (none)"
    fi
    echo "Uncategorized subdirectories: $uncategorized"

    exit 0
fi

# ---- Dirs-Only Listing Mode ----
if [[ "$DIRS_ONLY" == true ]]; then
    # Collect dirs with metadata into a temp file for sorting
    TMPFILE=$(mktemp /tmp/list-directory.XXXXXX)
    trap 'rm -f "$TMPFILE"' EXIT

    while IFS= read -r d; do
        [[ -z "$d" ]] && continue

        dirname_val=$(basename "$d")

        # Size via du -sh
        dir_size_human=$(du -sh "$d" 2>/dev/null | cut -f1 | tr -d '[:space:]')

        # Modified date via stat
        dir_mtime=$(stat -f '%m' "$d" 2>/dev/null || echo 0)

        # Tab-separated: mtime|dirname|fullpath|size_human
        printf '%s\t%s\t%s\t%s\n' "$dir_mtime" "$dirname_val" "$d" "$dir_size_human" >> "$TMPFILE"
    done < <(collect_dirs)

    TOTAL_FILTERED=$(wc -l < "$TMPFILE" | tr -d ' ')

    if [[ "$TOTAL_FILTERED" -eq 0 ]]; then
        echo "=== Directory (subdirectories): $DIR ==="
        echo "No uncategorized subdirectories found."
        exit 0
    fi

    # Sort
    case "$SORT_BY" in
        date) SORT_KEY="-k1,1n" ;;
        name) SORT_KEY="-k2,2" ;;
        *)    SORT_KEY="-k1,1n" ;;
    esac

    if [[ "$SORT_ORDER" == "desc" ]]; then
        SORT_FLAG="-r"
    else
        SORT_FLAG=""
    fi

    SORTED_FILE=$(mktemp /tmp/list-directory-sorted.XXXXXX)
    trap 'rm -f "$TMPFILE" "$SORTED_FILE"' EXIT

    sort -t$'\t' $SORT_KEY $SORT_FLAG "$TMPFILE" > "$SORTED_FILE"

    # Apply pagination
    START=$((OFFSET + 1))
    END=$((OFFSET + LIMIT))
    PAGE_FILE=$(mktemp /tmp/list-directory-page.XXXXXX)
    trap 'rm -f "$TMPFILE" "$SORTED_FILE" "$PAGE_FILE"' EXIT

    sed -n "${START},${END}p" "$SORTED_FILE" > "$PAGE_FILE"
    PAGE_COUNT=$(wc -l < "$PAGE_FILE" | tr -d ' ')

    # Header
    echo "=== Directory (subdirectories): $DIR ==="
    echo "Total: $TOTAL_FILTERED subdirectories | Showing $((OFFSET + 1))-$((OFFSET + PAGE_COUNT)) of $TOTAL_FILTERED"
    echo ""

    # Format each dir entry
    DIR_IDX=$((OFFSET + 1))
    while IFS=$'\t' read -r mtime dname fullpath size_human; do
        [[ -z "$dname" ]] && continue

        # Format date
        date_str=$(date -r "$mtime" "+%Y-%m-%d" 2>/dev/null || echo "unknown")

        # Item count
        item_count=$(find "$fullpath" -type f 2>/dev/null | wc -l | tr -d ' ')

        # Contents summary (extension breakdown)
        contents=$(get_contents_summary "$fullpath")

        echo "--- Dir $DIR_IDX ---"
        echo "Name: $dname"
        echo "Size: $size_human"
        echo "Modified: $date_str"
        echo "Items: $item_count files"
        echo "Contents: $contents"
        echo ""

        DIR_IDX=$((DIR_IDX + 1))
    done < "$PAGE_FILE"

    exit 0
fi

# ---- Summary Mode ----
if [[ "$SUMMARY" == true ]]; then
    echo "=== Directory Summary: $DIR ==="
    echo ""

    # Collect all files — use individual variables (bash 3.2 has no associative arrays)
    count_images=0; size_images=0
    count_documents=0; size_documents=0
    count_spreadsheets=0; size_spreadsheets=0
    count_archives=0; size_archives=0
    count_installers=0; size_installers=0
    count_applications=0; size_applications=0
    count_videos=0; size_videos=0
    count_audio=0; size_audio=0
    count_code=0; size_code=0
    count_other=0; size_other=0
    total_count=0
    total_size=0

    # Age buckets
    now=$(date +%s)
    age_7d=0
    age_30d=0
    age_90d=0
    age_older=0

    cutoff_7d=$((now - 7 * 86400))
    cutoff_30d=$((now - 30 * 86400))
    cutoff_90d=$((now - 90 * 86400))

    while IFS= read -r file; do
        [[ -z "$file" ]] && continue

        filename=$(basename "$file")
        ext=$(get_extension "$filename")
        category=$(classify_extension "$ext")

        # Get file size and modification time using stat (BSD macOS)
        file_size=$(stat -f '%z' "$file" 2>/dev/null || echo 0)
        file_mtime=$(stat -f '%m' "$file" 2>/dev/null || echo 0)

        # Increment per-category counters
        eval "count_${category}=\$(( count_${category} + 1 ))"
        eval "size_${category}=\$(( size_${category} + file_size ))"
        total_count=$((total_count + 1))
        total_size=$((total_size + file_size))

        # Age buckets (cumulative)
        if [[ $file_mtime -ge $cutoff_7d ]]; then
            age_7d=$((age_7d + 1))
        fi
        if [[ $file_mtime -ge $cutoff_30d ]]; then
            age_30d=$((age_30d + 1))
        fi
        if [[ $file_mtime -ge $cutoff_90d ]]; then
            age_90d=$((age_90d + 1))
        fi
        if [[ $file_mtime -lt $cutoff_90d ]]; then
            age_older=$((age_older + 1))
        fi
    done < <(collect_files)

    if [[ $total_count -eq 0 ]]; then
        echo "Total: 0 files"
        echo ""
        echo "Directory is empty (no files at top level)."
        exit 0
    fi

    echo "Total: $total_count files, $(human_size $total_size)"
    echo ""

    # By Type — display in fixed order
    echo "By Type:"
    for category in images documents spreadsheets archives installers applications videos audio code other; do
        eval "count=\$count_${category}"
        if [[ $count -gt 0 ]]; then
            eval "size=\$size_${category}"
            exts=$(type_extensions "$category")
            # Capitalize category name
            first_char=$(echo "${category}" | cut -c1 | tr '[:lower:]' '[:upper:]')
            rest=$(echo "${category}" | cut -c2-)
            label="${first_char}${rest}"
            echo "  $label ($exts): $count files, $(human_size $size)"
        fi
    done
    echo ""

    # By Age
    echo "By Age:"
    echo "  Last 7 days: $age_7d files"
    echo "  Last 30 days: $age_30d files"
    echo "  Last 90 days: $age_90d files"
    echo "  Older than 90 days: $age_older files"
    echo ""

    # Existing subfolders
    subfolders=()
    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        subfolders+=("$(basename "$d")/")
    done < <(find "$DIR" -maxdepth 1 -type d ! -path "$DIR" 2>/dev/null | sort)

    if [[ ${#subfolders[@]} -gt 0 ]]; then
        echo "Existing subfolders: $(IFS=', '; echo "${subfolders[*]}")"
    else
        echo "Existing subfolders: (none)"
    fi

    exit 0
fi

# ---- Listing Mode ----

# Collect files with metadata into a temp file for sorting
TMPFILE=$(mktemp /tmp/list-directory.XXXXXX)
trap 'rm -f "$TMPFILE"' EXIT

while IFS= read -r file; do
    [[ -z "$file" ]] && continue

    filename=$(basename "$file")
    ext=$(get_extension "$filename")

    # Apply type filter
    if ! matches_filter "$ext" "$FILTER_TYPE"; then
        continue
    fi

    # Get metadata using stat (BSD macOS)
    file_size=$(stat -f '%z' "$file" 2>/dev/null || echo 0)
    file_mtime=$(stat -f '%m' "$file" 2>/dev/null || echo 0)

    # Tab-separated: mtime|size|name|ext|fullpath
    printf '%s\t%s\t%s\t%s\t%s\n' "$file_mtime" "$file_size" "$filename" "$ext" "$file" >> "$TMPFILE"
done < <(collect_files)

TOTAL_FILTERED=$(wc -l < "$TMPFILE" | tr -d ' ')

if [[ "$TOTAL_FILTERED" -eq 0 ]]; then
    echo "=== Directory: $DIR ==="
    if [[ -n "$FILTER_TYPE" ]]; then
        echo "No $FILTER_TYPE files found."
    else
        echo "No files found."
    fi
    exit 0
fi

# Sort the temp file
# Columns: 1=mtime, 2=size, 3=name, 4=ext, 5=fullpath
case "$SORT_BY" in
    date)
        SORT_KEY="-k1,1n"
        ;;
    size)
        SORT_KEY="-k2,2n"
        ;;
    name)
        SORT_KEY="-k3,3"
        ;;
    type)
        SORT_KEY="-k4,4"
        ;;
    *)
        SORT_KEY="-k1,1n"
        ;;
esac

if [[ "$SORT_ORDER" == "desc" ]]; then
    SORT_FLAG="-r"
else
    SORT_FLAG=""
fi

SORTED_FILE=$(mktemp /tmp/list-directory-sorted.XXXXXX)
trap 'rm -f "$TMPFILE" "$SORTED_FILE"' EXIT

sort -t$'\t' $SORT_KEY $SORT_FLAG "$TMPFILE" > "$SORTED_FILE"

# Apply pagination
START=$((OFFSET + 1))
END=$((OFFSET + LIMIT))
PAGE_FILE=$(mktemp /tmp/list-directory-page.XXXXXX)
trap 'rm -f "$TMPFILE" "$SORTED_FILE" "$PAGE_FILE"' EXIT

sed -n "${START},${END}p" "$SORTED_FILE" > "$PAGE_FILE"
PAGE_COUNT=$(wc -l < "$PAGE_FILE" | tr -d ' ')

# Header
echo "=== Directory: $DIR ==="
if [[ -n "$FILTER_TYPE" ]]; then
    echo "Filter: $FILTER_TYPE"
fi
echo "Total: $TOTAL_FILTERED files | Showing $((OFFSET + 1))-$((OFFSET + PAGE_COUNT)) of $TOTAL_FILTERED"
echo ""

# Format each file entry
FILE_IDX=$((OFFSET + 1))
while IFS=$'\t' read -r mtime size name ext fullpath; do
    [[ -z "$name" ]] && continue

    # Format date
    date_str=$(date -r "$mtime" "+%Y-%m-%d" 2>/dev/null || echo "unknown")

    # Format size
    size_str=$(human_size "$size")

    # Type description
    type_desc=$(type_description "$ext")

    echo "--- File $FILE_IDX ---"
    echo "Name: $name"
    echo "Size: $size_str"
    echo "Modified: $date_str"
    echo "Type: $type_desc"
    if [[ -n "$ext" ]]; then
        echo "Extension: .$ext"
    fi
    echo ""

    FILE_IDX=$((FILE_IDX + 1))
done < "$PAGE_FILE"
