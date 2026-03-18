import { sleep } from "workflow";

type AppUser = {
  id: string;
  email: string;
};

async function createUser(email: string): Promise<AppUser> {
  // Replace this with your database insert.
  return {
    id: crypto.randomUUID(),
    email,
  };
}

async function sendWelcomeEmail(user: AppUser): Promise<void> {
  // Replace this with your email provider integration.
  console.log("welcome_email", user.email);
}

async function sendOnboardingEmail(user: AppUser): Promise<void> {
  // Replace this with your email provider integration.
  console.log("onboarding_email", user.email);
}

export async function handleUserSignup(email: string) {
  "use workflow";

  const user = await createUser(email);
  await sendWelcomeEmail(user);

  await sleep("5s");

  await sendOnboardingEmail(user);
  return { userId: user.id, status: "onboarded" };
}
