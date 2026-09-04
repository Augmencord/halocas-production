"use client";

import React, { useState, useRef } from "react";
import Image from "next/image";
import {
  X,
  UploadCloud,
  Camera,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ShieldCheck,
  ShieldAlert,
  User,
  HardHat,
  Building,
  Mail,
  ScanFace,
} from "lucide-react";
import {
  createWorker,
  enrollWorkerFace,
  WorkerCreatePayload,
  WorkerItem,
} from "@/lib/api";

interface AddWorkerModalProps {
  isOpen: boolean;
  departments: string[];
  onClose: () => void;
  onSuccess: (newWorker: WorkerItem) => void;
}

export function AddWorkerModal({
  isOpen,
  departments,
  onClose,
  onSuccess,
}: AddWorkerModalProps): React.JSX.Element | null {
  const [name, setName] = useState<string>("");
  const [role, setRole] = useState<string>("");
  const [department, setDepartment] = useState<string>(departments[0] || "Operations");
  const [supervisorEmail, setSupervisorEmail] = useState<string>("");
  const [isAuthorized, setIsAuthorized] = useState<boolean>(false);

  // Photo upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitStep, setSubmitStep] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (file: File): void => {
    if (!file.type.startsWith("image/")) {
      setErrorMsg("Invalid file format. Please upload a JPEG, PNG, or WEBP image.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg("Image size exceeds 10MB limit.");
      return;
    }

    setErrorMsg(null);
    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>): void => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleClearPhoto = (): void => {
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMsg("Worker full name is required.");
      return;
    }
    if (!role.trim()) {
      setErrorMsg("Worker operational role is required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setSubmitStep("Registering personnel profile...");

    try {
      const payload: WorkerCreatePayload = {
        name: name.trim(),
        role: role.trim(),
        department: department.trim(),
        supervisor_email: supervisorEmail.trim() || undefined,
        is_authorized: isAuthorized,
      };

      const worker = await createWorker(payload);

      if (selectedFile) {
        setSubmitStep("Extracting Facenet512 512-D facial embedding...");
        try {
          const enrollResult = await enrollWorkerFace(worker.id, selectedFile);
          worker.has_face_embedding = true;
          worker.face_photo_url = enrollResult.photoUrl;
        } catch (enrollErr) {
          // Log warning but let worker be created
          console.warn("Face enrollment warning:", enrollErr);
        }
      }

      onSuccess(worker);
      onClose();
    } catch (err) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Failed to register worker profile. Check backend connection."
      );
    } finally {
      setIsSubmitting(false);
      setSubmitStep("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-xl my-8 rounded-3xl bg-[#1f2937] border border-[#374151] p-6 shadow-2xl space-y-6 text-white animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#374151]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[#00FFFF]/10 border border-[#00FFFF]/30 text-[#00FFFF]">
              <ScanFace className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Enroll New Personnel
              </h3>
              <p className="text-xs text-gray-400">
                Register mine worker credentials and DeepFace biometric facial signature.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error Alert */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-[#FF3B30]/15 border border-[#FF3B30]/40 flex items-center gap-2.5 text-xs text-[#FF3B30]">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Two-Column Form Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Full Name */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-[#00FFFF]" />
                Full Legal Name <span className="text-[#FF3B30]">*</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Marcus Vance"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF]"
                required
              />
            </div>

            {/* Role */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <HardHat className="w-3.5 h-3.5 text-[#00FFFF]" />
                Operational Role <span className="text-[#FF3B30]">*</span>
              </label>
              <input
                type="text"
                placeholder="e.g. Haul Truck Escort"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF]"
                required
              />
            </div>

            {/* Department */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-[#00FFFF]" />
                Department
              </label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white focus:outline-none focus:border-[#00FFFF]"
              >
                {departments.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            {/* Supervisor Email */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-300 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-[#00FFFF]" />
                Supervisor Alert Email
              </label>
              <input
                type="email"
                placeholder="supervisor@halocas-mine.internal"
                value={supervisorEmail}
                onChange={(e) => setSupervisorEmail(e.target.value)}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#00FFFF]"
              />
            </div>
          </div>

          {/* Hazard Authorization Switch */}
          <div className="p-3.5 rounded-xl bg-[#111827] border border-[#374151] flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-xs font-bold text-white flex items-center gap-1.5">
                {isAuthorized ? (
                  <ShieldCheck className="w-4 h-4 text-[#10B981]" />
                ) : (
                  <ShieldAlert className="w-4 h-4 text-[#F59E0B]" />
                )}
                <span>Hazardous Zone Machinery Clearance</span>
              </div>
              <p className="text-[11px] text-gray-400">
                {isAuthorized
                  ? "Authorized mechanic/operator. Proximity breaches within 3.0m will NOT trigger supervisor sirens."
                  : "Restricted personnel. Proximity breaches will instantly trigger supervisor notifications."}
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isAuthorized}
                onChange={(e) => setIsAuthorized(e.target.checked)}
                disabled={isSubmitting}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#00FFFF]"></div>
            </label>
          </div>

          {/* Face Photo Biometric Upload Area */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-gray-300 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Camera className="w-3.5 h-3.5 text-[#00FFFF]" />
                Facial Biometric Portrait (Facenet512)
              </span>
              <span className="text-[10px] text-gray-400 font-mono">
                Optional for registration, required for auto-detection
              </span>
            </label>

            {previewUrl ? (
              /* Image Preview with Detection Reticle Overlay */
              <div className="relative rounded-2xl bg-[#111827] border border-[#374151] overflow-hidden p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="relative w-20 h-20 rounded-xl overflow-hidden border-2 border-[#00FFFF]/80 bg-black">
                    <Image
                      src={previewUrl}
                      alt="Biometric portrait preview"
                      width={80}
                      height={80}
                      className="w-full h-full object-cover"
                      unoptimized
                    />
                    {/* Simulated Biometric Crosshair Reticle */}
                    <div className="absolute inset-0 border border-[#00FFFF]/40 pointer-events-none" />
                    <div className="absolute top-1 left-1 w-2 h-2 border-t-2 border-l-2 border-[#00FFFF]" />
                    <div className="absolute top-1 right-1 w-2 h-2 border-t-2 border-r-2 border-[#00FFFF]" />
                    <div className="absolute bottom-1 left-1 w-2 h-2 border-b-2 border-l-2 border-[#00FFFF]" />
                    <div className="absolute bottom-1 right-1 w-2 h-2 border-b-2 border-r-2 border-[#00FFFF]" />
                  </div>

                  <div className="space-y-1">
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
                      <span>Portrait Loaded</span>
                    </div>
                    <div className="text-[11px] text-gray-400 font-mono truncate max-w-xs">
                      {selectedFile?.name} (
                      {selectedFile
                        ? (selectedFile.size / (1024 * 1024)).toFixed(2)
                        : "0"}{" "}
                      MB)
                    </div>
                    <div className="text-[10px] text-[#00FFFF] font-mono">
                      Ready for 512-D embedding extraction
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleClearPhoto}
                  disabled={isSubmitting}
                  className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white text-xs font-semibold transition-colors"
                >
                  Replace
                </button>
              </div>
            ) : (
              /* Drag and drop upload zone */
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
                  isDragging
                    ? "border-[#00FFFF] bg-[#00FFFF]/5"
                    : "border-[#374151] hover:border-[#00FFFF]/50 bg-[#111827]/40"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
                <UploadCloud className="w-8 h-8 text-gray-400 mx-auto mb-2 group-hover:text-[#00FFFF]" />
                <div className="text-xs font-semibold text-white">
                  Drop worker face photo here, or{" "}
                  <span className="text-[#00FFFF] underline underline-offset-2">
                    browse files
                  </span>
                </div>
                <div className="text-[11px] text-gray-400 mt-1">
                  High-resolution front-facing portrait (JPG, PNG, WEBP max 10MB)
                </div>
              </div>
            )}
          </div>

          {/* Modal Actions */}
          <div className="pt-4 border-t border-[#374151] flex items-center justify-between">
            <div className="text-xs text-gray-400 font-mono">
              {isSubmitting && (
                <div className="flex items-center gap-2 text-[#00FFFF]">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{submitStep}</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-xl bg-[#111827] border border-[#374151] text-xs font-semibold text-gray-300 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-[#00FFFF] text-[#111827] text-xs font-bold hover:bg-[#00FFFF]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md shadow-[#00FFFF]/20"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Complete Enrollment</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
