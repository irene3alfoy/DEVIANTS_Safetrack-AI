"""SafeTrack AI's initial interface; no AI processing is performed yet."""

import streamlit as st


def render_sidebar() -> None:
    """Collect settings reserved for the next development phase."""
    with st.sidebar:
        st.title("SafeTrack AI")
        st.caption("MVP Status: Development")
        st.divider()
        st.number_input(
            "Restricted-zone threshold (seconds)",
            min_value=1,
            value=10,
            step=1,
            key="restricted_zone_threshold",
            help="Future analysis will use this prolonged-presence threshold. "
            "No analysis runs in this dashboard version.",
        )


def render_introduction() -> None:
    """Introduce the project's purpose without implying inference is active."""
    st.title("SafeTrack AI")
    st.subheader("Autonomous Vision & Behaviour Understanding")
    st.divider()
    st.header("Problem Statement")
    st.write(
        "Video surveillance often requires continuous human monitoring to "
        "recognise safety concerns. SafeTrack AI is being developed to analyse "
        "video, detect people and objects, track them over time, and identify "
        "abnormal behaviour with supporting evidence. This initial dashboard "
        "provides video input and preview; the analysis pipeline is not active yet."
    )


def render_video_input() -> None:
    """Preview the user's uploaded bytes without saving to a local file."""
    st.header("Video Input")
    uploaded_video = st.file_uploader(
        "Upload a video",
        type=["mp4", "mov", "avi"],
        help="Supported inputs: MP4, MOV and AVI. Playback depends on the browser's codec support.",
    )
    if uploaded_video is None:
        st.caption("No video selected. Upload your footage to preview it.")
        return

    # Use the original upload directly: no sample video or AI data is substituted.
    st.text(f"File name: {uploaded_video.name}")
    st.text(f"File size: {uploaded_video.size / (1024 * 1024):.2f} MB")
    formats = {"mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo"}
    extension = uploaded_video.name.rsplit(".", 1)[-1].lower()
    st.video(uploaded_video.getvalue(), format=formats.get(extension, "video/mp4"), autoplay=False)
    st.caption(
        "Some MOV or AVI codecs cannot play in a browser. "
        "If the preview fails, upload an H.264 MP4 version."
    )
    st.info(
        "AI analysis pipeline will process this video in the next development phase."
    )


def render_analysis_results() -> None:
    """Display honest placeholders rather than fabricated counts or events."""
    st.header("Analysis Results")
    st.caption("Results will appear here once the AI analysis pipeline is implemented.")
    placeholders = (
        ("Detected People", "People detection is not implemented yet."),
        ("Active Tracking IDs", "Entity tracking is not implemented yet."),
        ("Abnormal Events", "Behaviour analysis is not implemented yet."),
        ("Evidence", "Supporting frames and clips are not generated yet."),
    )
    # Two compact rows keep placeholders readable without a crowded dashboard.
    for offset in range(0, len(placeholders), 2):
        for column, (title, message) in zip(st.columns(2), placeholders[offset : offset + 2]):
            with column:
                with st.container(border=True):
                    st.subheader(title)
                    st.caption(message)


def main() -> None:
    # Configure the page before creating any Streamlit interface elements.
    st.set_page_config(page_title="SafeTrack AI", page_icon="🎥", layout="centered")
    render_sidebar()
    render_introduction()
    render_video_input()
    st.divider()
    render_analysis_results()

    # Explain the planned MVP and finish with the requested project identifier.
    st.header("MVP Scope")
    st.write("Current MVP: Detect prolonged presence inside a predefined restricted zone.")
    st.divider()
    st.caption("HackNEX 2026 | HNX26PSI07")


if __name__ == "__main__":
    main()

