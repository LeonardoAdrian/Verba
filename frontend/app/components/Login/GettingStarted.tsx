"use client";

import React, { useEffect, useRef } from "react";
import VerbaButton from "../Navigation/VerbaButton";
import { FaHeart, FaGlobe } from "react-icons/fa";

interface GettingStartedComponentProps {
  addStatusMessage: (
    message: string,
    type: "INFO" | "WARNING" | "SUCCESS" | "ERROR"
  ) => void;
}

const GettingStartedComponent: React.FC<GettingStartedComponentProps> = ({
  addStatusMessage,
}) => {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (dialogRef.current) {
      dialogRef.current.showModal();
    }
  }, []);

  return (
    <dialog id={"Getting-Started-Modal"} className="modal" ref={dialogRef}>
      <div className="modal-box w-11/12 max-w-5xl">
        <div className="hero">
          <div className="hero-content flex-row">
            <div className="text-center lg:text-left">
              <h1 className="text-2xl md:text-5xl font-bold">
                Bienvenido a Inti App
              </h1>
              <h2 className="text-lg md:text-2xl mt-2">
                Una solución para charlar con tus datos
              </h2>
              <p className="py-6 text-sm md:text-base">
                Esta aplicación es un demo hecho para mostrar una oferta
                de aplicación end-to-end optimizada y amigable para el usuario
                de Retrieval-Augmented Generation (RAG).
              </p>
              <div className="flex flex-col md:flex-row gap-2">
                <VerbaButton
                  title="Intisoluciones"
                  Icon={FaGlobe}
                  onClick={() =>
                    window.open("https://www.intisoluciones.com", "_blank")
                  }
                />
              </div>
            </div>
            <div className="hidden md:block shrink-0">
              <img
                src="https://raw.githubusercontent.com/LeonardoAdrian/Verba/refs/heads/main/imgs/inti_logo.png"
                alt="Inti App"
                width={400}
                className="rounded-lg shadow-2xl"
              />
            </div>
          </div>
        </div>
        <div className="modal-action mt-6 justify-center md:justify-end">
          <form method="dialog">
            <VerbaButton
              title="Comenzar!"
              type="submit"
              selected={true}
              onClick={() => {
                addStatusMessage(
                  "Welcome to Inti App!",
                  "SUCCESS"
                );
              }}
              selected_color="bg-primary-verba"
              Icon={FaHeart}
            />
          </form>
        </div>
      </div>
    </dialog>
  );
};

export default GettingStartedComponent;
