"use client";

import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import {
  Play,
  Pause,
  Volume2,
  Volume1,
  VolumeX,
  Maximize,
  Minimize,
  Download,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  Film,
  Loader2,
  Sliders,
} from "lucide-react";

export interface TimelineMarker {
  time: number; // In seconds
  label: string;
  color?: "red" | "amber" | "cyan" | "green";
  description?: string;
}

export interface VideoPlayerProps {
  src?: string | null;
  poster?: string;
  title?: string;
  incidentId?: number | string;
  markers?: TimelineMarker[];
  fps?: number;
  autoPlay?: boolean;
  loop?: boolean;
  className?: string;
}

export function VideoPlayer({
  src,
  poster,
  title,
  incidentId,
  markers = [],
  fps = 30,
  autoPlay = false,
  loop = false,
  className = "",
}: VideoPlayerProps): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const progressBarRef = useRef<HTMLDivElement>(null);

  // Playback state
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [bufferedEnd, setBufferedEnd] = useState<number>(0);

  // Volume & Speed
  const [volume, setVolume] = useState<number>(1);
  const [isMuted, setIsMuted] = useState<boolean>(true); // Default muted for autoplay policy
  const [playbackRate, setPlaybackRate] = useState<number>(1);
  const [showSpeedMenu, setShowSpeedMenu] = useState<boolean>(false);

  // Display & UI state
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const [isControlsVisible, setIsControlsVisible] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [hasError, setHasError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  // Scrubbing & Hover Preview
  const [isScrubbing, setIsScrubbing] = useState<boolean>(false);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [hoverPosition, setHoverPosition] = useState<number>(0);
  const [activeMarkerTooltip, setActiveMarkerTooltip] = useState<TimelineMarker | null>(null);

  const hideControlsTimer = useRef<NodeJS.Timeout | null>(null);

  const speedOptions = [0.25, 0.5, 1.0, 1.5, 2.0];

  const resetControlsTimer = useCallback(() => {
    setIsControlsVisible(true);
    if (hideControlsTimer.current) {
      clearTimeout(hideControlsTimer.current);
    }
    if (isPlaying) {
      hideControlsTimer.current = setTimeout(() => {
        setIsControlsVisible(false);
        setShowSpeedMenu(false);
      }, 2500);
    }
  }, [isPlaying]);

  // Auto-hide controls when video is playing
  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    const timer = setTimeout(() => {
      setIsControlsVisible(false);
      setShowSpeedMenu(false);
    }, 2500);
    return () => {
      clearTimeout(timer);
    };
  }, [isPlaying]);

  // Fullscreen change listener
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, []);

  // Format seconds into MM:SS.ff (minutes:seconds.hundredths)
  const formatTime = (timeInSeconds: number): string => {
    if (isNaN(timeInSeconds) || timeInSeconds < 0) return "00:00.00";
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    const hundredths = Math.floor((timeInSeconds % 1) * 100);
    return `${minutes.toString().padStart(2, "0")}:${seconds
      .toString()
      .padStart(2, "0")}.${hundredths.toString().padStart(2, "0")}`;
  };

  // Current Frame calculation
  const currentFrame = useMemo(() => {
    return Math.floor(currentTime * fps);
  }, [currentTime, fps]);

  const totalFrames = useMemo(() => {
    return Math.floor((duration || 0) * fps);
  }, [duration, fps]);

  // Toggle Play / Pause
  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => {
          setIsPlaying(false);
        });
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  // Seek video
  const seekTo = useCallback(
    (timeInSeconds: number) => {
      if (!videoRef.current) return;
      const clamped = Math.max(0, Math.min(timeInSeconds, duration || 0));
      videoRef.current.currentTime = clamped;
      setCurrentTime(clamped);
    },
    [duration]
  );

  // Frame-by-Frame Stepping
  const stepFrame = useCallback(
    (direction: 1 | -1) => {
      if (!videoRef.current) return;
      // Pause video when stepping frames
      if (!videoRef.current.paused) {
        videoRef.current.pause();
        setIsPlaying(false);
      }
      const frameDelta = 1 / fps;
      seekTo(videoRef.current.currentTime + direction * frameDelta);
    },
    [fps, seekTo]
  );

  // Volume & Mute
  const handleVolumeChange = (newVolume: number) => {
    if (!videoRef.current) return;
    const clamped = Math.max(0, Math.min(1, newVolume));
    setVolume(clamped);
    videoRef.current.volume = clamped;
    if (clamped === 0) {
      setIsMuted(true);
      videoRef.current.muted = true;
    } else if (isMuted) {
      setIsMuted(false);
      videoRef.current.muted = false;
    }
  };

  const toggleMute = useCallback(() => {
    if (!videoRef.current) return;
    if (isMuted) {
      videoRef.current.muted = false;
      setIsMuted(false);
      if (volume === 0) {
        setVolume(0.5);
        videoRef.current.volume = 0.5;
      }
    } else {
      videoRef.current.muted = true;
      setIsMuted(true);
    }
  }, [isMuted, volume]);

  // Playback Rate
  const handleRateChange = (rate: number) => {
    if (!videoRef.current) return;
    videoRef.current.playbackRate = rate;
    setPlaybackRate(rate);
    setShowSpeedMenu(false);
  };

  // Fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen?.().catch((err) => {
        console.warn("Fullscreen request error:", err);
      });
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  }, []);

  // Video Scrubbing Handlers
  const handleScrubStart = (e: React.MouseEvent<HTMLDivElement>) => {
    setIsScrubbing(true);
    handleScrubMove(e);
  };

  const handleScrubMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressBarRef.current || duration <= 0) return;
    const rect = progressBarRef.current.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const targetTime = ratio * duration;
    setHoverTime(targetTime);
    setHoverPosition(ratio * 100);

    if (isScrubbing) {
      seekTo(targetTime);
    }
  };

  const handleScrubEnd = () => {
    setIsScrubbing(false);
  };

  // Clip Download
  const handleDownload = async () => {
    if (!src) return;
    setIsDownloading(true);
    const filename = `halocas_incident_${incidentId || "clip"}_${Date.now()}.mp4`;

    try {
      const response = await fetch(src);
      if (!response.ok) throw new Error("Failed to fetch clip binary");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      // Fallback to opening link directly
      const a = document.createElement("a");
      a.href = src;
      a.download = filename;
      a.target = "_blank";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } finally {
      setIsDownloading(false);
    }
  };

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if container is focused or active element is inside container
      if (
        !containerRef.current ||
        !containerRef.current.contains(document.activeElement)
      ) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        if (e.shiftKey) {
          stepFrame(-1);
        } else {
          seekTo(currentTime - 2);
        }
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        if (e.shiftKey) {
          stepFrame(1);
        } else {
          seekTo(currentTime + 2);
        }
      } else if (e.code === "Comma") {
        e.preventDefault();
        stepFrame(-1);
      } else if (e.code === "Period") {
        e.preventDefault();
        stepFrame(1);
      } else if (e.code === "KeyF") {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.code === "KeyM") {
        e.preventDefault();
        toggleMute();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [togglePlay, stepFrame, seekTo, currentTime, toggleMute, toggleFullscreen]);

  // Marker Color Helper
  const getMarkerColorClasses = (color?: string) => {
    switch (color) {
      case "red":
        return {
          bg: "bg-[#FF3B30]",
          shadow: "shadow-[0_0_8px_rgba(255,59,48,0.8)]",
          border: "border-[#FF3B30]",
          text: "text-[#FF3B30]",
        };
      case "amber":
        return {
          bg: "bg-[#F59E0B]",
          shadow: "shadow-[0_0_8px_rgba(245,158,11,0.8)]",
          border: "border-[#F59E0B]",
          text: "text-[#F59E0B]",
        };
      case "green":
        return {
          bg: "bg-[#10B981]",
          shadow: "shadow-[0_0_8px_rgba(16,185,129,0.8)]",
          border: "border-[#10B981]",
          text: "text-[#10B981]",
        };
      case "cyan":
      default:
        return {
          bg: "bg-[#00FFFF]",
          shadow: "shadow-[0_0_8px_rgba(0,255,255,0.8)]",
          border: "border-[#00FFFF]",
          text: "text-[#00FFFF]",
        };
    }
  };

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setHoverTime(null);
        setActiveMarkerTooltip(null);
      }}
      onMouseMove={resetControlsTimer}
      className={`relative group select-none rounded-2xl bg-[#0B0F17] border border-[#374151] overflow-hidden focus:outline-none focus:border-[#00FFFF]/50 shadow-2xl transition-all ${className}`}
    >
      {/* Video Element */}
      {src ? (
        <video
          ref={videoRef}
          src={src}
          poster={poster}
          autoPlay={autoPlay}
          loop={loop}
          muted={isMuted}
          playsInline
          preload="metadata"
          onClick={togglePlay}
          onTimeUpdate={() => {
            if (videoRef.current) {
              setCurrentTime(videoRef.current.currentTime);
            }
          }}
          onDurationChange={() => {
            if (videoRef.current) {
              setDuration(videoRef.current.duration);
              setIsLoading(false);
            }
          }}
          onProgress={() => {
            if (videoRef.current && videoRef.current.buffered.length > 0) {
              setBufferedEnd(
                videoRef.current.buffered.end(
                  videoRef.current.buffered.length - 1
                )
              );
            }
          }}
          onWaiting={() => setIsLoading(true)}
          onPlaying={() => {
            setIsLoading(false);
            setIsPlaying(true);
            setHasError(false);
          }}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
          onError={() => {
            setIsLoading(false);
            setHasError(true);
            setErrorMessage(
              "Unable to load incident video stream. URL may have expired or format is unsupported."
            );
          }}
          className="w-full h-full object-contain cursor-pointer aspect-video"
        />
      ) : (
        /* Standby HUD pattern when no video is attached */
        <div className="w-full aspect-video flex flex-col items-center justify-center p-6 text-center bg-[#0B0F17] border border-[#374151]/50">
          <Film className="w-12 h-12 text-gray-600 mb-3" />
          <div className="text-sm font-mono font-bold text-white uppercase">
            H.264 Incident Stream Offline
          </div>
          <p className="text-xs text-gray-400 font-mono mt-1 max-w-sm">
            {incidentId
              ? `No raw buffer recording associated with Incident #${incidentId}.`
              : "No video source provided."}
          </p>
        </div>
      )}

      {/* Top HUD Telemetry Bar */}
      <div
        className={`absolute top-0 inset-x-0 p-3 bg-gradient-to-b from-black/80 via-black/40 to-transparent flex items-center justify-between pointer-events-none transition-opacity duration-200 ${
          isControlsVisible || !isPlaying ? "opacity-100" : "opacity-0"
        }`}
      >
        <div className="flex items-center gap-2">
          <div className="px-2 py-0.5 rounded bg-[#111827]/90 border border-[#374151] text-[10px] font-mono text-[#00FFFF] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#00FFFF] animate-pulse" />
            <span>{title || `INCIDENT ARCHIVE #${incidentId || "PLAYBACK"}`}</span>
          </div>
          <div className="px-2 py-0.5 rounded bg-[#111827]/90 border border-[#374151] text-[10px] font-mono text-gray-300">
            FPS: {fps}
          </div>
        </div>

        <div className="text-[10px] font-mono text-gray-400 bg-[#111827]/80 px-2 py-0.5 rounded border border-[#374151]">
          FRAME: {currentFrame} / {totalFrames || "---"}
        </div>
      </div>

      {/* Center Buffering Spinner */}
      {isLoading && !hasError && src && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50 backdrop-blur-xs pointer-events-none">
          <Loader2 className="w-10 h-10 text-[#00FFFF] animate-spin mb-2" />
          <div className="text-xs font-mono text-gray-200">
            Buffering Incident Clip...
          </div>
        </div>
      )}

      {/* Center Big Play Button (When Paused) */}
      {!isPlaying && !isLoading && !hasError && src && (
        <button
          onClick={togglePlay}
          className="absolute inset-0 m-auto w-16 h-16 rounded-full bg-[#00FFFF]/20 border-2 border-[#00FFFF] flex items-center justify-center text-[#00FFFF] shadow-[0_0_20px_rgba(0,255,255,0.4)] hover:scale-110 hover:bg-[#00FFFF]/30 transition-all cursor-pointer z-10"
          title="Play Video (Space)"
        >
          <Play className="w-7 h-7 ml-1" />
        </button>
      )}

      {/* Error State Overlay */}
      {hasError && (
        <div className="absolute inset-0 bg-[#0B0F17]/95 flex flex-col items-center justify-center p-6 text-center space-y-3 z-20">
          <div className="p-3 rounded-full bg-[#FF3B30]/20 border border-[#FF3B30]/40 text-[#FF3B30]">
            <AlertCircle className="w-8 h-8" />
          </div>
          <div className="text-sm font-bold text-white">
            Playback Stream Error
          </div>
          <p className="text-xs text-gray-400 max-w-sm font-mono">
            {errorMessage}
          </p>
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => {
                setHasError(false);
                setIsLoading(true);
                if (videoRef.current) {
                  videoRef.current.load();
                }
              }}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#1f2937] border border-[#374151] hover:border-[#00FFFF] text-xs font-semibold text-white transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Stream</span>
            </button>
            {src && (
              <a
                href={src}
                target="_blank"
                rel="noreferrer"
                className="px-3.5 py-1.5 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 transition-colors"
              >
                Open Direct URL
              </a>
            )}
          </div>
        </div>
      )}

      {/* Bottom Controls Bar Overlay */}
      <div
        className={`absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/95 via-black/80 to-transparent p-3 pt-6 space-y-2.5 transition-opacity duration-200 z-10 ${
          isControlsVisible || !isPlaying || isHovered
            ? "opacity-100 pointer-events-auto"
            : "opacity-0 pointer-events-none"
        }`}
      >
        {/* Timeline Seek Bar & Markers Container */}
        <div
          ref={progressBarRef}
          onMouseDown={handleScrubStart}
          onMouseMove={handleScrubMove}
          onMouseUp={handleScrubEnd}
          className="relative h-4 flex items-center cursor-pointer group/bar"
        >
          {/* Base Track */}
          <div className="relative w-full h-1.5 bg-[#374151] rounded-full overflow-hidden group-hover/bar:h-2 transition-all">
            {/* Buffered Bar */}
            <div
              className="absolute top-0 left-0 bottom-0 bg-gray-600/60 rounded-full transition-all"
              style={{
                width: `${
                  duration > 0 ? (bufferedEnd / duration) * 100 : 0
                }%`,
              }}
            />
            {/* Played Progress Bar */}
            <div
              className="absolute top-0 left-0 bottom-0 bg-[#00FFFF] rounded-full shadow-[0_0_8px_#00FFFF] transition-all"
              style={{
                width: `${
                  duration > 0 ? (currentTime / duration) * 100 : 0
                }%`,
              }}
            />
          </div>

          {/* Hover Scrub Preview Line */}
          {hoverTime !== null && (
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-white/70 pointer-events-none"
              style={{ left: `${hoverPosition}%` }}
            />
          )}

          {/* Hover Scrub Time Tooltip */}
          {hoverTime !== null && (
            <div
              className="absolute -top-7 -translate-x-1/2 px-2 py-0.5 rounded bg-[#111827] border border-[#374151] text-[10px] font-mono text-white pointer-events-none shadow-lg z-30"
              style={{ left: `${hoverPosition}%` }}
            >
              {formatTime(hoverTime)}
            </div>
          )}

          {/* Timeline Proximity Markers */}
          {duration > 0 &&
            markers.map((marker, idx) => {
              const markerPercent = (marker.time / duration) * 100;
              const colorClasses = getMarkerColorClasses(marker.color);

              return (
                <div
                  key={idx}
                  onClick={(e) => {
                    e.stopPropagation();
                    seekTo(marker.time);
                  }}
                  onMouseEnter={() => setActiveMarkerTooltip(marker)}
                  onMouseLeave={() => setActiveMarkerTooltip(null)}
                  className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 flex items-center justify-center cursor-pointer z-20 hover:scale-125 transition-transform"
                  style={{ left: `${markerPercent}%` }}
                >
                  {/* Outer glowing halo */}
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${colorClasses.bg} ${colorClasses.shadow} border border-black`}
                  />
                </div>
              );
            })}

          {/* Marker Tooltip */}
          {activeMarkerTooltip && duration > 0 && (
            <div
              className="absolute -top-12 -translate-x-1/2 p-1.5 rounded-lg bg-[#111827]/95 border border-[#374151] text-[10px] font-mono text-white pointer-events-none shadow-xl z-30 whitespace-nowrap space-y-0.5"
              style={{
                left: `${(activeMarkerTooltip.time / duration) * 100}%`,
              }}
            >
              <div className="flex items-center gap-1.5 font-bold">
                <span
                  className={`w-2 h-2 rounded-full ${
                    getMarkerColorClasses(activeMarkerTooltip.color).bg
                  }`}
                />
                <span>{activeMarkerTooltip.label}</span>
                <span className="text-gray-400">
                  ({formatTime(activeMarkerTooltip.time)})
                </span>
              </div>
              {activeMarkerTooltip.description && (
                <div className="text-gray-400 text-[9px]">
                  {activeMarkerTooltip.description}
                </div>
              )}
            </div>
          )}

          {/* Draggable Scrubber Thumb */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 bg-white rounded-full border-2 border-[#00FFFF] shadow-[0_0_10px_#00FFFF] pointer-events-none transition-transform group-hover/bar:scale-110"
            style={{
              left: `${
                duration > 0 ? (currentTime / duration) * 100 : 0
              }%`,
            }}
          />
        </div>

        {/* Buttons and Readout Controls Row */}
        <div className="flex items-center justify-between text-xs text-gray-300">
          {/* Left Controls: Play/Pause, Frame-by-Frame, Time */}
          <div className="flex items-center gap-2">
            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              className="p-1.5 rounded-lg hover:bg-white/10 text-white transition-colors"
              title={isPlaying ? "Pause (Space)" : "Play (Space)"}
            >
              {isPlaying ? (
                <Pause className="w-4 h-4 text-[#00FFFF]" />
              ) : (
                <Play className="w-4 h-4 text-white" />
              )}
            </button>

            {/* Frame Step Backward */}
            <button
              onClick={() => stepFrame(-1)}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-300 hover:text-white transition-colors flex items-center"
              title="Step -1 Frame (Shift+Left / Comma)"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span className="text-[10px] font-mono -ml-0.5">1f</span>
            </button>

            {/* Frame Step Forward */}
            <button
              onClick={() => stepFrame(1)}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-300 hover:text-white transition-colors flex items-center"
              title="Step +1 Frame (Shift+Right / Period)"
            >
              <span className="text-[10px] font-mono -mr-0.5">1f</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>

            {/* Rewind to start */}
            <button
              onClick={() => seekTo(0)}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
              title="Restart Clip"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            {/* Time Display */}
            <div className="font-mono text-[11px] text-gray-300 ml-1">
              <span className="text-white font-bold">
                {formatTime(currentTime)}
              </span>
              <span className="text-gray-500 mx-1">/</span>
              <span className="text-gray-400">{formatTime(duration)}</span>
            </div>
          </div>

          {/* Right Controls: Volume, Speed, Download, Fullscreen */}
          <div className="flex items-center gap-2">
            {/* Volume Controls */}
            <div className="flex items-center gap-1.5 group/vol">
              <button
                onClick={toggleMute}
                className="p-1.5 rounded-lg hover:bg-white/10 text-gray-300 hover:text-white transition-colors"
                title={isMuted ? "Unmute (M)" : "Mute (M)"}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX className="w-4 h-4 text-gray-400" />
                ) : volume < 0.5 ? (
                  <Volume1 className="w-4 h-4 text-white" />
                ) : (
                  <Volume2 className="w-4 h-4 text-[#00FFFF]" />
                )}
              </button>

              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={isMuted ? 0 : volume}
                onChange={(e) =>
                  handleVolumeChange(parseFloat(e.target.value))
                }
                className="w-16 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[#00FFFF] group-hover/vol:w-20 transition-all"
                title="Volume Slider"
              />
            </div>

            {/* Playback Speed Menu */}
            <div className="relative">
              <button
                onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                className="px-2 py-1 rounded-lg bg-[#111827] border border-[#374151] hover:border-[#00FFFF] text-[11px] font-mono text-gray-200 hover:text-white flex items-center gap-1 transition-colors"
                title="Playback Speed"
              >
                <Sliders className="w-3 h-3 text-[#00FFFF]" />
                <span>{playbackRate}x</span>
              </button>

              {showSpeedMenu && (
                <div className="absolute bottom-8 right-0 rounded-xl bg-[#111827] border border-[#374151] p-1 shadow-2xl z-30 min-w-[75px] space-y-0.5">
                  {speedOptions.map((rate) => (
                    <button
                      key={rate}
                      onClick={() => handleRateChange(rate)}
                      className={`w-full text-left px-2.5 py-1 rounded-md text-[11px] font-mono transition-colors ${
                        playbackRate === rate
                          ? "bg-[#00FFFF]/20 text-[#00FFFF] font-bold"
                          : "text-gray-400 hover:text-white hover:bg-gray-800"
                      }`}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              disabled={isDownloading || !src}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-300 hover:text-[#00FFFF] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Download MP4 Clip"
            >
              {isDownloading ? (
                <Loader2 className="w-4 h-4 animate-spin text-[#00FFFF]" />
              ) : (
                <Download className="w-4 h-4" />
              )}
            </button>

            {/* Fullscreen Toggle */}
            <button
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg hover:bg-white/10 text-gray-300 hover:text-white transition-colors"
              title={
                isFullscreen ? "Exit Fullscreen (F)" : "Fullscreen (F)"
              }
            >
              {isFullscreen ? (
                <Minimize className="w-4 h-4 text-[#00FFFF]" />
              ) : (
                <Maximize className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
export default VideoPlayer;
