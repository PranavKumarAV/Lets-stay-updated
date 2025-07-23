import { Step } from "@/pages/home";

interface StepIndicatorProps {
  currentStep: Step;
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  const steps = [
    { number: 1, label: "Region" },
    { number: 2, label: "Topics" },
    { number: 3, label: "Sources" },
    { number: 4, label: "Results" },
  ];

  const getStepStatus = (stepNumber: number) => {
    if (typeof currentStep === "number" && stepNumber <= currentStep) {
      return "active";
    } else if (currentStep === "loading" && stepNumber <= 3) {
      return "active";
    }
    return "inactive";
  };

  return (
    <div className="mb-8">
      <div className="flex items-center justify-center space-x-4 mb-6">
        {steps.map((step, index) => (
          <div key={step.number} className="flex items-center">
            <div className="flex items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  getStepStatus(step.number) === "active"
                    ? "bg-primary text-white"
                    : "bg-gray-300 text-gray-600"
                }`}
              >
                {step.number}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  getStepStatus(step.number) === "active"
                    ? "text-primary"
                    : "text-gray-600"
                }`}
              >
                {step.label}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className="w-12 h-0.5 bg-gray-300 ml-4"></div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
