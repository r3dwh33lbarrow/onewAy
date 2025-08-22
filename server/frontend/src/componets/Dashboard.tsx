import {useAuthStore} from "../stores/authStore.ts";

export default function Dashboard() {
  const user = useAuthStore(state => state.user);

  return (
    <div>
      {user == null ? <h1>How did you get here?</h1> : <h1>Hello {user.username}</h1>}
    </div>
  );
}