import { useNavigate } from 'react-router';
import { AssessmentWizard } from './AssessmentWizard';
import { useAuth } from '../contexts/AuthContext';

export function AssessmentPage() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background p-4 sm:p-8">
      <div className="mx-auto max-w-5xl">
        <AssessmentWizard
          title="Vakify learning style assessment"
          description="Take this 20-question check to understand whether you learn best through visuals, audio, or hands-on practice. You can revisit it anytime from the dashboard."
          showSkip={false}
          continueLabel="Back to dashboard"
          onCompleted={async () => {
            await refreshUser();
            navigate('/dashboard', { replace: true });
          }}
        />
      </div>
    </div>
  );
}
