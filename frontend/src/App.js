import "@/App.css";
import { Toaster } from "@/components/ui/sonner";
import NestingStudio from "@/components/NestingStudio";

function App() {
  return (
    <div className="App">
      <NestingStudio />
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#141414",
            border: "1px solid #262626",
            color: "#fff",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: "12px",
          },
        }}
      />
    </div>
  );
}

export default App;
